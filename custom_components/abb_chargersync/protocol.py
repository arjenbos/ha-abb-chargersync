"""ChargerSync binary protocol over the cloud WebSocket, derived from Android SDK.

No Bluetooth transport. Mutations are never automatically replayed on timeout.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from functools import reduce

from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives.ciphers import Cipher, modes

from .api import ChargerSyncError, UnsupportedError
from .const import STATUSES


class ProtocolError(ChargerSyncError):
    """Malformed, rejected or incomplete device response."""


@dataclass(frozen=True)
class Frame:
    command: int
    code: int
    body: bytes


def encode(command: int, body: bytes = b"", token: bytes = bytes(8)) -> bytes:
    if len(token) != 8 or len(body) > 1024:
        raise ValueError("Invalid token or body length")
    header = struct.pack(
        "<BBBBHBB", 0xAA if command in (0xBA, 0xD9) else 0xFE, command, 0, 0, len(body), 0, 0
    )
    frame = bytearray(header + token + body)
    frame[7] = reduce(int.__xor__, frame, 0)
    return bytes(frame)


class FrameDecoder:
    """Bounded incremental parser: supports fragmented and concatenated replies."""

    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, raw: bytes) -> list[Frame]:
        self.buffer.extend(raw)
        if len(self.buffer) > 8192:
            self.buffer.clear()
            raise ProtocolError("Oversized frame stream")
        frames = []
        while len(self.buffer) >= 8:
            if self.buffer[0] not in (0xFE, 0xAA):
                self.buffer.clear()
                raise ProtocolError("Invalid frame marker")
            length = int.from_bytes(self.buffer[4:6], "little")
            if length > 1024:
                self.buffer.clear()
                raise ProtocolError("Invalid frame length")
            total = 16 + length
            if len(self.buffer) < total:
                break
            raw_frame = bytes(self.buffer[:total])
            del self.buffer[:total]
            if reduce(int.__xor__, raw_frame, 0):
                raise ProtocolError("Frame checksum mismatch")
            frames.append(Frame(raw_frame[1], raw_frame[2], raw_frame[16:]))
        return frames


def check_reply(frame: Frame) -> bytes:
    if frame.code in (20, 21):
        raise UnsupportedError("Device does not support command")
    if frame.code:
        raise ProtocolError(f"Device rejected command ({frame.code})")
    return frame.body


def identity_body(device_number: str, user_id: int = 0) -> bytes:
    """Legacy cloud identity handshake. SDK defaults mUserId to zero."""
    device = device_number.replace("-", "").encode("ascii")
    user = str(user_id).encode("ascii")
    if len(device) > 20 or len(user) > 15:
        raise ValueError("Invalid device or user identifier")
    clear = bytearray(48)
    clear[: len(device)] = device
    clear[20:22] = b"\x02\x01"
    clear[22 : 22 + len(user)] = user
    # Java DES/ECB/PKCS5Padding. Repeated-key TripleDES equals single DES.
    padded = bytes(clear) + b"\x08" * 8
    encryptor = Cipher(TripleDES(b"ucserver" * 3), modes.ECB()).encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return struct.pack("<H", 128) + encrypted.ljust(128, b"\0")


def identity_token(body: bytes) -> bytes:
    if len(body) < 34 or body[0] != 0:
        raise ProtocolError("Device identity authentication rejected")
    return body[26:34]


def configuration(body: bytes, expected: int) -> bytes:
    if len(body) < 5:
        raise ProtocolError("Truncated configuration reply")
    kind, result, length = struct.unpack_from("<HBH", body)
    if kind != expected:
        raise ProtocolError("Unexpected configuration type")
    if result:
        raise UnsupportedError("Configuration not supported")
    if len(body) != length + 5:
        raise ProtocolError("Invalid configuration length")
    return body[5:]


def parse_status(body: bytes) -> dict:
    if not body:
        raise ProtocolError("Empty status response")
    status = body[0]
    result = {"status_code": status, "status": STATUSES.get(status, "unknown")}
    if status == 15:
        if len(body) < 3:
            raise ProtocolError("Truncated fault response")
        result["fault_code"] = int.from_bytes(body[1:3], "little")
    elif status == 14:
        result["unavailable_codes"] = body[1:].hex()
    elif status == 6:
        if len(body) < 2:
            raise ProtocolError("Truncated charging response")
        three_phase = body[1] != 0
        fmt = "<BIHIHIHIHIB" if three_phase else "<BIHIHIB"
        needed = struct.calcsize(fmt)
        if len(body) != needed + 1:
            raise ProtocolError("Invalid charging status length")
        values = struct.unpack_from(fmt, body, 1)
        result.update(
            phase_type=values[0],
            session_id=str(values[1]),
            session_energy=values[2] / 100,
            voltage_l1=values[3] / 100,
            current_l1=values[4] / 100,
        )
        if three_phase:
            result.update(
                voltage_l2=values[5] / 100,
                current_l2=values[6] / 100,
                voltage_l3=values[7] / 100,
                current_l3=values[8] / 100,
                duration=values[9],
                rated_current=values[10],
            )
        else:
            result.update(duration=values[5], rated_current=values[6])
        # Apparent power is U*I, not guaranteed real active power.
        result["apparent_power"] = sum(
            result.get(f"voltage_l{i}", 0) * result.get(f"current_l{i}", 0) for i in (1, 2, 3)
        )
    return result


def parse_solar_status(body: bytes) -> dict:
    if not body or body[0] != 6:
        return parse_status(body)
    if len(body) < 2:
        raise ProtocolError("Truncated solar status")
    three = body[1] != 0
    fmt = "<BII IHIHIHIBIHHH" if three else "<BIIIHIBIH"
    fmt = fmt.replace(" ", "")
    if len(body) != struct.calcsize(fmt) + 1:
        raise ProtocolError("Invalid solar status length")
    v = struct.unpack_from(fmt, body, 1)
    result = {
        "status_code": 6,
        "status": "charging",
        "phase_type": v[0],
        "session_id": str(v[1]),
        "session_energy": v[2] / 1000,
        "voltage_l1": v[3] / 100,
        "current_l1": v[4] / 100,
    }
    if three:
        result.update(
            voltage_l2=v[5] / 100,
            current_l2=v[6] / 100,
            voltage_l3=v[7] / 100,
            current_l3=v[8] / 100,
            duration=v[9],
            rated_current=v[10],
            solar_energy=v[11] / 1000,
            solar_current_l1=v[12] / 100,
            solar_current_l2=v[13] / 100,
            solar_current_l3=v[14] / 100,
        )
    else:
        result.update(
            duration=v[5], rated_current=v[6], solar_energy=v[7] / 1000, solar_current_l1=v[8] / 100
        )
    result["apparent_power"] = sum(
        result.get(f"voltage_l{i}", 0) * result.get(f"current_l{i}", 0) for i in (1, 2, 3)
    )
    if result["session_energy"] > 0:
        result["solar_percentage"] = min(
            100, result["solar_energy"] / result["session_energy"] * 100
        )
    return result


def parse_limits(body: bytes) -> dict:
    if len(body) < 7 or body[0]:
        raise ProtocolError("Invalid load-balancing response")
    _, valid, enabled, mode, delay, ranges_enabled = struct.unpack_from("<BBBBHB", body)
    ranges = []
    if ranges_enabled:
        if len(body) < 8 or len(body) != 8 + body[7] * 10:
            raise ProtocolError("Invalid load-balancing ranges")
        for pos in range(8, len(body), 10):
            weekdays, start, end, limit = struct.unpack_from("<BIIB", body, pos)
            ranges.append({"weekdays": weekdays, "from": start, "to": end, "limit": limit})
    return {
        "random_valid": valid,
        "random_enabled": enabled,
        "random_mode": mode,
        "random_delay": delay,
        "enabled": bool(ranges_enabled),
        "ranges": ranges,
    }


def encode_limits(mode: int, settings: dict) -> bytes:
    ranges = settings["ranges"]
    if len(ranges) > 50:
        raise ValueError("Too many ranges")
    body = struct.pack(
        "<BBBBHBB",
        mode,
        settings["random_valid"],
        settings["random_enabled"],
        settings["random_mode"],
        settings["random_delay"],
        int(settings["enabled"]),
        len(ranges),
    )
    return body + b"".join(
        struct.pack("<BIIB", r["weekdays"], r["from"], r["to"], r["limit"]) for r in ranges
    )


SOLAR_OFFSETS = {
    "solar_start_current": (0, "<f"),
    "solar_start_wait": (4, "<B"),
    "solar_charging_current": (5, "<f"),
    "solar_charging_wait": (9, "<B"),
    "eco_start_current": (10, "<f"),
    "eco_start_wait": (14, "<B"),
    "eco_charging_current": (15, "<f"),
    "eco_charging_wait": (19, "<B"),
}


def parse_solar_offsets(raw: bytes) -> dict:
    if len(raw) != 20:
        raise ProtocolError("Invalid solar threshold configuration")
    return {
        name: struct.unpack_from(fmt, raw, offset)[0]
        for name, (offset, fmt) in SOLAR_OFFSETS.items()
    }
