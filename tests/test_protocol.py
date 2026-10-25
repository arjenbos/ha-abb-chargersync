import struct

import pytest
from cryptography.hazmat.decrepit.ciphers.algorithms import TripleDES
from cryptography.hazmat.primitives.ciphers import Cipher, modes

from custom_components.abb_chargersync.api import UnsupportedError
from custom_components.abb_chargersync.protocol import (
    ConfigurationUnavailableError,
    Frame,
    FrameDecoder,
    ProtocolError,
    check_reply,
    configuration,
    encode,
    encode_limits,
    identity_body,
    identity_token,
    parse_limits,
    parse_solar_status,
    parse_status,
)


def test_request_known_vector():
    # Manually calculated FE B5 00 00 01 00 00 4A, eight zero token bytes, port 00.
    assert encode(181, b"\0").hex() == "feb500000100004a000000000000000000"


def test_decoder_fragmented_concatenated_and_corrupt():
    decoder = FrameDecoder()
    raw = encode(181, b"\x06", b"12345678")
    assert not decoder.feed(raw[:7])
    assert decoder.feed(raw[7:] + encode(224, b"\0\x20\x10")) == [
        Frame(181, 0, b"\x06"),
        Frame(224, 0, b"\0\x20\x10"),
    ]
    bad = bytearray(raw)
    bad[-1] ^= 1
    with pytest.raises(ProtocolError, match="checksum"):
        decoder.feed(bad)
    with pytest.raises(ProtocolError, match="length"):
        FrameDecoder().feed(bytes.fromhex("feb50000ffff0000"))


def test_identity_matches_java_cleartext_layout_and_padding():
    raw = identity_body("TEST123")
    assert len(raw) == 130 and raw[:2] == b"\x80\0"
    decryptor = Cipher(TripleDES(b"ucserver" * 3), modes.ECB()).decryptor()
    clear = decryptor.update(raw[2:58]) + decryptor.finalize()
    assert clear[:20] == b"TEST123".ljust(20, b"\0")
    assert clear[20:23] == b"\x02\x010"
    assert clear[-8:] == b"\x08" * 8
    assert raw[58:] == bytes(72)
    assert identity_token(bytes(26) + b"12345678") == b"12345678"
    with pytest.raises(ProtocolError):
        identity_token(b"\xff")


@pytest.mark.parametrize("code", [20, 21])
def test_unsupported(code):
    with pytest.raises(UnsupportedError):
        check_reply(Frame(181, code, b""))


def test_configuration_validation():
    assert configuration(struct.pack("<HBH", 10, 0, 4) + b"\1\0\0\1", 10) == b"\1\0\0\1"
    with pytest.raises(ProtocolError):
        configuration(b"\0", 10)
    with pytest.raises(ConfigurationUnavailableError):
        configuration(struct.pack("<HBH", 10, 1, 0), 10)
    with pytest.raises(ConfigurationUnavailableError) as error:
        configuration(struct.pack("<HB", 9, 1), 9)
    assert error.value.result_code == 1


def test_single_phase_measurements_and_idle_unknown():
    result = parse_status(b"\6" + struct.pack("<BIHIHIB", 0, 42, 125, 23000, 1600, 3600, 32))
    assert result["session_energy"] == 1.25
    assert result["voltage_l1"] == 230
    assert result["current_l1"] == 16
    assert result["apparent_power"] == 3680
    assert result["duration"] == 3600
    assert "voltage_l2" not in result
    assert parse_status(b"\0") == {"status_code": 0, "status": "available"}
    with pytest.raises(ProtocolError):
        parse_status(b"\6\0")


def test_three_phase_status():
    result = parse_status(
        b"\6"
        + struct.pack("<BIHIHIHIHIB", 1, 3, 456, 23000, 1000, 23100, 1100, 23200, 1200, 120, 16)
    )
    assert result["current_l3"] == 12
    assert result["duration"] == 120


def test_solar_units_from_apk():
    result = parse_solar_status(
        b"\6" + struct.pack("<BIIIHIBIH", 0, 42, 2000, 23000, 1600, 600, 32, 1500, 1200)
    )
    assert result["session_energy"] == 2
    assert result["solar_energy"] == 1.5
    assert result["solar_percentage"] == 75
    assert result["solar_current_l1"] == 12
    three = parse_solar_status(
        b"\6"
        + struct.pack(
            "<BIIIHIHIHIBIHHH",
            1,
            42,
            2000,
            23000,
            1600,
            23000,
            1600,
            23000,
            1600,
            600,
            32,
            1500,
            1200,
            1200,
            1200,
        )
    )
    assert three["current_l3"] == 16
    assert three["solar_energy"] == 1.5


def test_load_limit_settings_preserved():
    settings = dict(
        random_valid=1,
        random_enabled=1,
        random_mode=2,
        random_delay=600,
        enabled=True,
        ranges=[dict(weekdays=31, **{"from": 0, "to": 3600}, limit=10)],
    )
    raw = encode_limits(5, settings)
    assert parse_limits(b"\0" + raw[1:]) == settings
    with pytest.raises(ProtocolError):
        parse_limits(b"\0")


def test_status_accepts_firmware_extension_after_known_fields():
    # The Android SDK reads the known prefix and permits trailing firmware fields.
    body = b"\6" + struct.pack(
        "<BIIIHIHIHIBIHHH",
        1,
        42,
        2000,
        23000,
        1600,
        23100,
        1500,
        23200,
        1400,
        600,
        32,
        1500,
        1200,
        1100,
        1000,
    )
    assert len(body + b"\0") == 44
    assert parse_solar_status(body + b"\0") == parse_solar_status(body)
    with pytest.raises(ProtocolError):
        parse_solar_status(body[:-1])
