"""Typed device operations; writes preserve unrelated device configuration."""

from __future__ import annotations

import asyncio
import struct
from collections.abc import Awaitable, Callable

from .api import AuthenticationError, ChargerSyncError, UnsupportedError
from .const import MODES
from .protocol import ProtocolError, encode_limits, parse_limits, parse_solar_status, parse_status
from .websocket import RemoteCharger


class ChargerController:
    def __init__(self, remote: RemoteCharger) -> None:
        self.remote = remote
        self.unsupported: set[str] = set()
        self.read_failures: dict[str, dict] = {}
        self._write_lock = asyncio.Lock()

    async def optional(self, name: str, read: Callable[[], Awaitable]) -> object | None:
        if name in self.unsupported:
            return None
        try:
            return await read()
        except UnsupportedError:
            self.unsupported.add(name)
            return None

    async def status(self) -> dict:
        if "solar_status" not in self.unsupported:
            body = await self.optional("solar_status", lambda: self.remote.command(175, b"\0"))
            if body is not None:
                return parse_solar_status(body)
        return parse_status(await self.remote.command(181, b"\0"))

    async def settings(self) -> dict:
        """Keep successful settings even when another capability cannot be read."""
        result = {}
        self.read_failures = {}
        for key, kind in (
            ("power", None),
            ("free_charging", None),
            ("active_mode", 9),
            ("default_mode", 10),
            ("eco_threshold", 38),
            ("cable", 3),
        ):
            data = None
            try:
                if key == "free_charging":
                    data = await self.optional(key, lambda: self.remote.command(221))
                elif kind is None:
                    data = await self.optional(key, lambda: self.remote.command(224))
                else:
                    data = await self.optional(
                        key, lambda k=kind: self.remote.query_configuration(k)
                    )
                if data is not None:
                    result.update(self._parse_setting(key, data))
            except AuthenticationError:
                raise
            except ChargerSyncError as err:
                failure = {"error": type(err).__name__}
                if isinstance(getattr(err, "result_code", None), int):
                    failure["result_code"] = err.result_code
                if isinstance(data, bytes):
                    failure["response_length"] = len(data)
                if isinstance(self.remote.last_error, dict):
                    failure.update(self.remote.last_error)
                self.read_failures[key] = failure
        return result

    @staticmethod
    def _parse_setting(key: str, data: bytes) -> dict:
        if key == "free_charging":
            if not data:
                raise ProtocolError("Missing device configuration")
            return {"free_charging": bool(data[0] & 0x04)}
        if key == "power":
            if not 3 <= len(data) <= 6:
                raise ProtocolError("Invalid current limit response")
            return {
                "port": data[0],
                "maximum_current": data[1],
                "current_limit": int.from_bytes(data[2:], "little"),
            }
        if key == "active_mode":
            if not data or data[0] not in MODES.values():
                raise ProtocolError("Invalid active mode")
            return {"active_mode": next(k for k, v in MODES.items() if v == data[0])}
        if key == "default_mode":
            if len(data) < 4 or data[3] not in MODES.values() or (data[3] == 2 and len(data) < 5):
                raise ProtocolError("Invalid default mode")
            return {
                "default_mode": next(k for k, v in MODES.items() if v == data[3]),
                "solar_enabled": bool(data[0]),
                "solar_delay": data[2],
                "solar_min_current": data[4] if data[3] == 2 else 0,
            }
        if key == "eco_threshold":
            if len(data) != 1:
                raise ProtocolError("Invalid threshold configuration")
            return {"ignore_eco_threshold": bool(data[0])}
        if key == "cable" and len(data) == 1 and data[0] in (1, 2):
            return {"cable_locked": data[0] == 1}
        return {}

    async def simple(self, command: int, body: bytes = b"") -> None:
        result = await self.remote.command(command, body)
        if command in (180, 192, 209, 231, 164) and (not result or result[0]):
            raise ProtocolError("Device action rejected")
        if command == 182 and len(result) < 4:
            raise ProtocolError("Truncated stop acknowledgement")
        if command in (209, 231) and len(result) >= 3 and int.from_bytes(result[1:3], "little"):
            raise ProtocolError("Cable operation failed")

    async def set_current(self, current: int) -> None:
        async with self._write_lock:
            power = await self.remote.command(224)
            parsed = self._parse_setting("power", power)
            if not 6 <= current <= parsed["maximum_current"]:
                raise ProtocolError("Current outside device limits")
            await self.simple(192, bytes((power[0], current)))

    async def set_free_charging(self, enabled: bool) -> None:
        """Change only the authorization bit, matching the official app's read-modify-write."""
        async with self._write_lock:
            config = await self.remote.command(221)
            self._parse_setting("free_charging", config)
            value = config[0] | 0x04 if enabled else config[0] & ~0x04
            # The SDK sends the updated configuration byte followed by reserved zero.
            result = await self.remote.command(220, bytes((value, 0)))
            if not result or result[0] != 0:
                raise ProtocolError("Free charging configuration rejected")

    async def set_mode(
        self,
        mode: str,
        *,
        active: bool = False,
        minimum: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        async with self._write_lock:
            if mode not in MODES:
                raise ValueError("Invalid mode")
            if active:
                await self.remote.configure(
                    4, bytes((MODES[mode],)) + (b"\0" if mode == "eco_mix" else b"")
                )
                return
            old = await self.remote.query_configuration(10)
            if len(old) < 4 or (old[3] == 2 and len(old) < 5):
                raise ProtocolError("Cannot preserve solar configuration")
            minimum = minimum if minimum is not None else old[4] if old[3] == 2 else 0
            if not 0 <= minimum <= 6:
                raise ValueError("Minimum solar current outside 0..6 A")
            is_enabled = old[0] if enabled is None else int(enabled)
            wire_mode = mode if is_enabled else "max_speed"
            body = bytes((is_enabled, old[1], old[2], MODES[wire_mode]))
            if wire_mode == "eco_mix":
                body += bytes((minimum,))
            await self.remote.configure(3, body)

    async def skip_delay(self) -> None:
        async with self._write_lock:
            settings = parse_limits(await self.remote.command(164, b"\x02"))
            settings["random_valid"] = 1
            await self.simple(164, encode_limits(3, settings))

    async def replace_limits(self, ranges: list[dict], enabled: bool) -> None:
        async with self._write_lock:
            settings = parse_limits(await self.remote.command(164, b"\x02"))
            power = await self.remote.command(224)
            self._parse_setting("power", power)
            for r in ranges:
                if not (
                    1 <= r["weekdays"] <= 127
                    and 0 <= r["from"] < r["to"] <= 86400
                    and 0 <= r["limit"] <= power[1]
                ):
                    raise ValueError("Invalid current-limit time range")
            settings.update(ranges=ranges, enabled=enabled)
            await self.simple(164, encode_limits(5, settings))

    async def set_solar_offsets(self, settings: dict) -> None:
        """Patch supported offsets while retaining every unspecified threshold/wait time."""
        async with self._write_lock:
            raw = bytearray(await self.remote.query_configuration(12))
            if len(raw) != 20:
                raise ProtocolError("Cannot preserve solar threshold configuration")
            from .protocol import SOLAR_OFFSETS

            for name, value in settings.items():
                offset, fmt = SOLAR_OFFSETS[name]
                struct.pack_into(fmt, raw, offset, value)
            await self.remote.configure(5, bytes(raw))
