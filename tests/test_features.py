"""App-derived capability gates and read-only cloud resources."""

from copy import deepcopy
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.abb_chargersync.api import ChargerSyncClient, ChargerSyncError
from custom_components.abb_chargersync.const import DOMAIN
from custom_components.abb_chargersync.lock import lock_supported, release_supported

# Captured at import, before the autouse fixture replaces them for setup tests.
FIRMWARE_NOTICE = ChargerSyncClient.firmware_notice
RFID_CARDS = ChargerSyncClient.rfid_cards


@pytest.mark.parametrize(
    ("device", "release", "lock"),
    [
        ({"outlet": "socket", "softVersion": "1.8.37"}, True, True),
        ({"outlet": "socket", "softVersion": "1.7.0"}, True, False),
        ({"outlet": "socket", "softVersion": "V1.6.5"}, False, False),
        ({"outlet": "socket", "softVersion": "1.6.5", "productType": 1}, True, True),
        ({"outlet": "cable", "softVersion": "1.8.37"}, False, False),
        ({}, True, True),
    ],
)
def test_cable_capabilities_follow_the_app(device, release, lock):
    assert release_supported(device) is release
    assert lock_supported(device) is lock


async def test_client_notice_and_cards_validation():
    client = ChargerSyncClient(Mock())
    client._request = AsyncMock(return_value={"title": "Update", "content": None})
    assert await FIRMWARE_NOTICE(client, "N") == {"title": "Update", "content": ""}
    assert client._request.await_args.kwargs["params"] == {
        "deviceNumber": "N",
        "type": "firmware_upgrade",
    }
    client._request.return_value = {}
    assert await FIRMWARE_NOTICE(client, "N") is None
    client._request.return_value = [{"id": "1"}]
    assert await RFID_CARDS(client) == [{"id": "1"}]
    assert client._request.await_args.kwargs["params"] == {"showHidden": "false"}
    client._request.return_value = {"error": True}
    with pytest.raises(ChargerSyncError):
        await RFID_CARDS(client)


DEVICE = {
    "id": 1,
    "deviceNumber": "TEST123",
    "aliasNumber": "Driveway",
    "softVersion": "1.7.0",
    "outlet": "socket",
    "online": 1,
}
STATE = {"status": "available", "status_code": 0}
SETTINGS = {
    "cable_locked": False,
    "lifetime_energy": 2500.5,
    "meter_status": 1,
    "modbus_status": 0,
}
CARDS = [
    {"id": "a", "name": "Car", "serialNumber": "SECRET-SERIAL", "deviceId": 1},
    {"id": "b", "name": "Account", "serialNumber": "OTHER", "deviceId": None},
    {"id": "c", "name": "Elsewhere", "serialNumber": "X", "deviceId": 9},
]


async def test_feature_entities_and_cable_lock_gate(hass, account_reads):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="42", data={"username": "a@example.com", "token": {}}
    )
    entry.add_to_hass(hass)
    account_reads["rfid_cards"].return_value = deepcopy(CARDS)
    account_reads["firmware_notice"].return_value = {"title": "New firmware", "content": "Info"}
    with (
        patch(
            "custom_components.abb_chargersync.api.ChargerSyncClient.devices",
            return_value=[deepcopy(DEVICE)],
        ),
        patch("custom_components.abb_chargersync.api.ChargerSyncClient.read", return_value=[]),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.status",
            return_value=STATE,
        ),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.settings",
            return_value=SETTINGS,
        ),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.simple",
            new_callable=AsyncMock,
        ) as simple,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        lifetime = hass.states.get("sensor.driveway_lifetime_energy")
        assert lifetime.state == "2500.5"
        assert lifetime.attributes["state_class"] == "total_increasing"
        assert hass.states.get("sensor.driveway_grid_meter_status").state == "1"
        cards = hass.states.get("sensor.driveway_rfid_cards")
        assert cards.state == "2" and cards.attributes["names"] == ["Car", "Account"]
        assert "SECRET-SERIAL" not in str(cards.attributes)
        notice = hass.states.get("sensor.driveway_firmware_notice")
        assert notice.state == "New firmware" and notice.attributes["content"] == "Info"
        # Firmware 1.7.0 supports release (1.6.8+) but not locking (1.8.2+), like the app.
        await hass.services.async_call(
            "lock", "unlock", {"entity_id": "lock.driveway_charging_cable"}, blocking=True
        )
        simple.assert_awaited_once_with(209)
        with pytest.raises(HomeAssistantError, match="does not support locking"):
            await hass.services.async_call(
                "lock", "lock", {"entity_id": "lock.driveway_charging_cable"}, blocking=True
            )
        assert simple.await_count == 1
        from homeassistant.helpers import device_registry as dr

        device = dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, "TEST123"), entry.entry_id
        )
        response = await hass.services.async_call(
            DOMAIN,
            "get_data",
            {"device_id": device.id, "resource": "rfid_cards"},
            blocking=True,
            return_response=True,
        )
        assert [c["name"] for c in response["result"]] == ["Car", "Account"]
        assert "serialNumber" not in response["result"][0]
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_tethered_outlet_has_no_cable_lock(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="42", data={"username": "a@example.com", "token": {}}
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.abb_chargersync.api.ChargerSyncClient.devices",
            return_value=[{**DEVICE, "outlet": "cable", "softVersion": "1.8.37"}],
        ),
        patch("custom_components.abb_chargersync.api.ChargerSyncClient.read", return_value=[]),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.status",
            return_value=STATE,
        ),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.settings",
            return_value=SETTINGS,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get("lock.driveway_charging_cable") is None
        assert await hass.config_entries.async_unload(entry.entry_id)
