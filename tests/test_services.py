from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import probatio
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ServiceValidationError

from custom_components.abb_chargersync.api import ChargerSyncError, UnsupportedError
from custom_components.abb_chargersync.services import SCHEMAS, execute, resolve


@pytest.fixture
def coordinator():
    return SimpleNamespace(
        client=AsyncMock(), async_request_refresh=AsyncMock(), controllers={}, _rest_updated=1
    )


async def test_schedule_ownership_prevents_cross_device_changes(coordinator):
    c = coordinator
    c.client.read.return_value = [{"id": 10}]
    with pytest.raises(ServiceValidationError):
        await execute(c, 1, "delete_schedule", {"schedule_id": 11})
    c.client.delete_schedule.assert_not_called()
    await execute(c, 1, "delete_schedule", {"schedule_id": 10})
    c.client.delete_schedule.assert_awaited_once_with(10)


async def test_tariff_patch_preserves_other_fields(coordinator):
    c = coordinator
    c.client.read.return_value = {
        "id": 99,
        "deviceId": 1,
        "averagePrice": "0.3",
        "currencyType": 1,
        "offPeakPrice": "0.2",
        "pinCode": "secret",
    }
    await execute(c, 1, "set_price", {"settings": {"averagePrice": 0.4}})
    c.client.set_price.assert_awaited_once_with(
        1, {"averagePrice": "0.4", "currencyType": 1, "offPeakPrice": "0.2"}
    )


async def test_get_history_uses_only_get_and_filters(coordinator):
    data = SCHEMAS["get_data"]({"device_id": "ha-id", "resource": "sessions", "company_only": True})
    await execute(coordinator, 1, "get_data", data)
    coordinator.client.read.assert_awaited_once_with(
        1, "sessions", page=0, per_page=20, isCompanyCarSession=1
    )


async def test_session_must_belong_to_charger(coordinator):
    c = coordinator
    c.client.read.return_value = {"data": [{"orderId": "right"}]}
    with pytest.raises(ServiceValidationError):
        await execute(c, 1, "set_company_session", {"session_id": "wrong", "company": True})
    c.client.set_company_session.assert_not_called()
    await execute(c, 1, "set_company_session", {"session_id": "right", "company": False})
    c.client.set_company_session.assert_awaited_once_with("right", False)


@pytest.mark.parametrize(
    "service,data",
    [
        ("create_schedule", {"device_id": "d", "start_time": "25:00", "end_time": "12:00"}),
        ("set_price", {"device_id": "d", "settings": {"rfidCards": []}}),
        ("set_auto_export", {"device_id": "d", "settings": {"enabled": True, "cycle": 2}}),
        ("get_data", {"device_id": "d", "resource": "sessions/active"}),
    ],
)
def test_schema_rejects_invalid_or_out_of_scope_inputs(service, data):
    with pytest.raises(probatio.Invalid):
        SCHEMAS[service](data)


async def test_auto_export_merges_existing_settings(coordinator):
    c = coordinator
    c.client.read.return_value = {
        "enabled": True,
        "format": "csv",
        "cycle": 3,
        "email": "private@example.com",
        "userId": 42,
    }
    await execute(c, 1, "set_auto_export", {"settings": {"enabled": False}})
    c.client.set_auto_export.assert_awaited_once_with(
        1, {"enabled": False, "format": "csv", "cycle": 3, "email": "private@example.com"}
    )


async def test_export_uses_documented_wire_fields(coordinator):
    c = coordinator
    await execute(
        c,
        1,
        "export_sessions",
        {
            "email": "a@example.com",
            "format": "excel",
            "start_time": "start",
            "end_time": "end",
            "company_only": True,
        },
    )
    c.client.export_sessions.assert_awaited_once_with(
        1,
        {
            "email": "a@example.com",
            "format": "excel",
            "startTime": "start",
            "endTime": "end",
            "isCompanyCarSession": True,
        },
    )


async def test_load_limits_uses_official_read_mode(coordinator):
    controller = SimpleNamespace(remote=SimpleNamespace(command=AsyncMock(return_value=b"\0" * 7)))
    coordinator.controllers[1] = controller
    result = await execute(coordinator, 1, "get_data", {"resource": "load_limits"})
    controller.remote.command.assert_awaited_once_with(164, b"\x02")
    assert result["result"]["enabled"] is False
    assert result["result"]["ranges"] == []


def test_resolve_uses_single_config_entry_owner():
    # No deprecated config_entries attribute: only the singular owner is available.
    device = SimpleNamespace(identifiers={("abb_chargersync", "TEST")}, config_entry_id="owner")
    owner = SimpleNamespace(data={1: {"device": {"deviceNumber": "TEST"}}})
    other = SimpleNamespace(data={2: {"device": {"deviceNumber": "TEST"}}})
    hass = Mock()
    hass.config_entries.async_entries.return_value = [
        SimpleNamespace(entry_id="other", state=ConfigEntryState.LOADED, runtime_data=other),
        SimpleNamespace(entry_id="owner", state=ConfigEntryState.LOADED, runtime_data=owner),
    ]
    with patch("custom_components.abb_chargersync.services.dr.async_get") as registry:
        registry.return_value.async_get.return_value = device
        assert resolve(hass, "ha-device") == (owner, 1)
        device.config_entry_id = "unloaded"
        with pytest.raises(ServiceValidationError, match="one loaded account"):
            resolve(hass, "ha-device")


async def test_unavailable_firmware_feed_is_explicit_optional_result(coordinator):
    coordinator.client.read.side_effect = UnsupportedError("Endpoint unavailable")
    result = await execute(coordinator, 1, "get_data", {"resource": "firmware"})
    assert result == {"result": {"available": False}}
    with pytest.raises(UnsupportedError):
        await execute(coordinator, 1, "get_data", {"resource": "schedules"})
    coordinator.client.read.side_effect = ChargerSyncError("Cannot connect to ChargerSync cloud")
    with pytest.raises(ChargerSyncError):
        await execute(coordinator, 1, "get_data", {"resource": "firmware"})
