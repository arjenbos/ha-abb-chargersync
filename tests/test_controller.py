from unittest.mock import AsyncMock, call

import pytest

from custom_components.abb_chargersync.api import UnsupportedError
from custom_components.abb_chargersync.controller import ChargerController
from custom_components.abb_chargersync.protocol import ProtocolError


async def test_current_limit_enforced_against_device():
    remote = AsyncMock()
    remote.command.side_effect = [b"\0\x10\x0a", b"\0"]
    controller = ChargerController(remote)
    await controller.set_current(12)
    assert remote.command.await_args_list[1].args == (192, b"\0\x0c")
    remote.command.side_effect = [b"\0\x10\x0a"]
    with pytest.raises(ProtocolError):
        await controller.set_current(17)
    remote.command.side_effect = [b"\0\x10\x0a"]
    with pytest.raises(ProtocolError):
        await controller.set_current(5)


async def test_preserve_other_solar_settings():
    remote = AsyncMock()
    remote.query_configuration.return_value = b"\1\0\x2a\2\4"
    controller = ChargerController(remote)
    await controller.set_mode("solar")
    remote.configure.assert_awaited_once_with(3, b"\1\0\x2a\3")
    remote.configure.reset_mock()
    await controller.set_mode("eco_mix", minimum=5)
    remote.configure.assert_awaited_once_with(3, b"\1\0\x2a\2\5")


async def test_unsupported_cached_and_lock_enum():
    remote = AsyncMock()
    remote.command.return_value = b"\0\x20\x10"

    async def configuration(kind):
        if kind == 3:
            return b"\2"
        raise UnsupportedError("not supported")

    remote.query_configuration.side_effect = configuration
    controller = ChargerController(remote)
    settings = await controller.settings()
    assert settings["cable_locked"] is False
    assert settings["current_limit"] == 16
    assert controller.unsupported == {"active_mode", "default_mode", "eco_threshold"}
    remote.query_configuration.reset_mock()
    await controller.settings()
    remote.query_configuration.assert_awaited_once_with(3)


async def test_rejected_cable_result_not_reported_as_success():
    remote = AsyncMock()
    remote.command.return_value = b"\0\x01\x01"
    with pytest.raises(ProtocolError):
        await ChargerController(remote).simple(209)


async def test_solar_offset_patch_preserves_other_fields():
    import struct

    remote = AsyncMock()
    original = struct.pack("<fBfBfBfB", 1.0, 30, 2.0, 60, 3.0, 90, 4.0, 120)
    remote.query_configuration.return_value = original
    controller = ChargerController(remote)
    await controller.set_solar_offsets({"eco_start_current": 2.5})
    expected = bytearray(original)
    struct.pack_into("<f", expected, 10, 2.5)
    remote.configure.assert_awaited_once_with(5, bytes(expected))


async def test_settings_failure_does_not_hide_other_capabilities():
    remote = AsyncMock()
    remote.command.return_value = b"\x00\x20\x10\x00"

    async def read(kind):
        return {9: b"\x01", 10: b"\x01\x00\x1e\x01", 38: b"\x00\x00", 3: b"\x02"}[kind]

    remote.query_configuration.side_effect = read
    c = ChargerController(remote)
    result = await c.settings()
    assert result["current_limit"] == 16
    assert result["maximum_current"] == 32
    assert result["default_mode"] == "max_speed"
    assert result["cable_locked"] is False
    assert c.read_failures == {"eco_threshold": {"error": "ProtocolError", "response_length": 2}}


async def test_load_limit_writes_read_mode_two_and_preserve_random_delay():
    remote = AsyncMock()
    # Result, random-valid/enabled/mode, delay=600, ranges disabled.
    original = b"\0\1\1\2\x58\2\0"
    remote.command.side_effect = [original, b"\0"]
    controller = ChargerController(remote)
    await controller.skip_delay()
    assert remote.command.await_args_list == [
        call(164, b"\x02"),
        call(164, b"\3" + original[1:] + b"\0"),
    ]
    remote.command.reset_mock()
    remote.command.side_effect = [original, b"\0\x20\x10", b"\0"]
    await controller.replace_limits([], False)
    assert remote.command.await_args_list == [
        call(164, b"\x02"),
        call(224),
        call(164, b"\5" + original[1:] + b"\0"),
    ]


@pytest.mark.parametrize("enabled,original,expected", [(True, 0xA1, 0xA5), (False, 0xA5, 0xA1)])
async def test_free_charging_preserves_other_configuration_bits(enabled, original, expected):
    remote = AsyncMock()
    remote.command.side_effect = [bytes((original, 0xFF)), b"\0"]
    await ChargerController(remote).set_free_charging(enabled)
    assert remote.command.await_args_list == [call(221), call(220, bytes((expected, 0)))]


@pytest.mark.parametrize("reply", [b"", b"\1"])
async def test_free_charging_rejects_missing_or_failed_acknowledgement(reply):
    remote = AsyncMock()
    remote.command.side_effect = [b"\0", reply]
    with pytest.raises(ProtocolError, match="rejected"):
        await ChargerController(remote).set_free_charging(True)
    assert remote.command.await_count == 2


async def test_free_charging_missing_configuration_never_writes():
    remote = AsyncMock()
    remote.command.return_value = b""
    with pytest.raises(ProtocolError, match="Missing device configuration"):
        await ChargerController(remote).set_free_charging(True)
    remote.command.assert_awaited_once_with(221)


def test_free_charging_read_uses_bit_two_without_result_prefix():
    assert ChargerController._parse_setting("free_charging", b"\xa5") == {"free_charging": True}
    assert ChargerController._parse_setting("free_charging", b"\xa1\xff") == {
        "free_charging": False
    }
