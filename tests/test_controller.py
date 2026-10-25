from unittest.mock import AsyncMock

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
