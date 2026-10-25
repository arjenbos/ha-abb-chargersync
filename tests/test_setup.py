from copy import deepcopy
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abb_chargersync.api import AuthenticationError
from custom_components.abb_chargersync.const import DOMAIN

DEVICE = {
    "id": 1,
    "deviceNumber": "TEST123",
    "aliasNumber": "Driveway",
    "model": "Terra AC",
    "softVersion": "1.8.0",
    "online": 1,
}
STATE = {
    "status": "charging",
    "status_code": 6,
    "current_l1": 16,
    "voltage_l1": 230,
    "session_energy": 1.2,
    "duration": 60,
}
SETTINGS = {
    "port": 0,
    "maximum_current": 32,
    "current_limit": 16,
    "default_mode": "eco_mix",
    "active_mode": "solar",
    "solar_enabled": True,
    "solar_min_current": 2,
    "ignore_eco_threshold": False,
    "cable_locked": True,
}


async def test_full_setup_entities_services_dynamic_devices_and_unload(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="42", data={"username": "a@example.com", "token": {}}
    )
    entry.add_to_hass(hass)
    devices = AsyncMock(return_value=[deepcopy(DEVICE)])

    async def read(device_id, resource, **kwargs):
        return {
            "schedules": [],
            "sessions": [],
            "price": {"averagePrice": "0.3", "currencyType": 1},
            "sessions/auto-export": {},
            "latest-upgrade-packages": [],
        }[resource]

    with (
        patch("custom_components.abb_chargersync.api.ChargerSyncClient.devices", devices),
        patch("custom_components.abb_chargersync.api.ChargerSyncClient.read", side_effect=read),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.status",
            return_value=STATE,
        ),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.settings",
            return_value=SETTINGS,
        ),
        patch(
            "custom_components.abb_chargersync.websocket.RemoteCharger.close",
            new_callable=AsyncMock,
        ) as close,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state == ConfigEntryState.LOADED
        assert hass.states.get("sensor.driveway_evcc_status").state == "C"
        assert hass.states.get("switch.driveway_charging_enabled").state == "on"
        assert hass.states.get("sensor.driveway_session_energy").state == "1.2"
        assert hass.states.get("lock.driveway_charging_cable").state == "locked"
        assert hass.states.get("number.driveway_charging_current_limit").state == "16"
        assert hass.states.get("select.driveway_default_charging_mode").state == "eco_mix"
        assert hass.services.has_service(DOMAIN, "get_data")
        registry = dr.async_get(hass)
        device = registry.async_get_device_by_identifier((DOMAIN, "TEST123"), entry.entry_id)
        response = await hass.services.async_call(
            DOMAIN,
            "get_data",
            {"device_id": device.id, "resource": "price"},
            blocking=True,
            return_response=True,
        )
        assert response["result"]["currencyType"] == 1
        devices.return_value = [
            {**DEVICE, "id": 2, "deviceNumber": "SECOND", "aliasNumber": "Garage"}
        ]
        entry.runtime_data._rest_updated = 0
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("sensor.driveway_session_energy").state == "unavailable"
        assert hass.states.get("sensor.garage_session_energy").state == "1.2"
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert close.await_count >= 2


async def test_offline_setup_then_reconnect(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="42", data={"username": "a@example.com", "token": {}}
    )
    entry.add_to_hass(hass)
    devices = AsyncMock(return_value=[{**DEVICE, "online": 0}])
    with (
        patch("custom_components.abb_chargersync.api.ChargerSyncClient.devices", devices),
        patch("custom_components.abb_chargersync.api.ChargerSyncClient.read", return_value=[]),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.status",
            return_value=STATE,
        ) as status,
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.settings",
            return_value=SETTINGS,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get("sensor.driveway_charging_status").state == "unavailable"
        status.assert_not_called()
        devices.return_value = [DEVICE]
        entry.runtime_data._rest_updated = 0
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        assert hass.states.get("sensor.driveway_session_energy").state == "1.2"
        await hass.config_entries.async_unload(entry.entry_id)


async def test_expired_account_requests_reauth(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="42", data={"username": "a@example.com", "token": {}}
    )
    entry.add_to_hass(hass)
    with patch(
        "custom_components.abb_chargersync.api.ChargerSyncClient.devices",
        side_effect=AuthenticationError,
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_token_rotation_does_not_reload_integration(hass):
    from custom_components.abb_chargersync import async_reload_entry

    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="42", data={"username": "a@example.com", "token": {}}
    )
    entry.add_to_hass(hass)
    from types import SimpleNamespace

    entry.runtime_data = SimpleNamespace(options_snapshot={})
    with patch.object(hass.config_entries, "async_reload") as reload:
        await async_reload_entry(hass, entry)
        reload.assert_not_called()
        hass.config_entries.async_update_entry(entry, options={"scan_interval": 60})
        await async_reload_entry(hass, entry)
        reload.assert_awaited_once_with(entry.entry_id)


async def test_diagnostics_exclude_all_identifiers_and_tokens(hass):
    import json
    from types import SimpleNamespace

    from custom_components.abb_chargersync.diagnostics import async_get_config_entry_diagnostics

    entry = SimpleNamespace(
        options={},
        data={"token": {"access_token": "secret-token"}},
        runtime_data=SimpleNamespace(
            data={
                1: {
                    "device": {**DEVICE, "pinCode": "secret-pin", "cipher": "secret-cipher"},
                    "state": {**STATE, "session_id": "secret-session"},
                    "resources": {"sessions": [{"user": "private"}]},
                }
            },
            controllers={1: SimpleNamespace(unsupported={"cable"})},
        ),
    )
    result = await async_get_config_entry_diagnostics(hass, entry)
    encoded = json.dumps(result)
    for private in [
        "secret-token",
        "secret-pin",
        "secret-cipher",
        "secret-session",
        "TEST123",
        "Driveway",
        "a@example.com",
    ]:
        assert private not in encoded


async def test_cable_write_rejected_while_charging(hass):
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.abb_chargersync.coordinator import ChargerSyncCoordinator

    entry = MockConfigEntry(domain=DOMAIN, data={"username": "a@example.com", "token": {}})
    entry.add_to_hass(hass)
    c = ChargerSyncCoordinator(hass, entry, AsyncMock())
    controller = AsyncMock()
    controller.status.return_value = {"status_code": 6}
    c.controllers[1] = controller
    import pytest

    with pytest.raises(HomeAssistantError, match="Stop charging"):
        await c.action(1, "unlock")
    controller.simple.assert_not_called()
    await c.async_shutdown()
