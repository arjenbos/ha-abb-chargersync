"""Resource availability, history units and credential-free management diagnostics."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from custom_components.abb_chargersync.frontend import async_setup_frontend
from custom_components.abb_chargersync.sensor import ResourceSensor
from custom_components.abb_chargersync.services import SCHEMAS, execute


def coordinator(resources):
    return SimpleNamespace(
        data={1: {"device": {"deviceNumber": "TEST", "online": 1}, "resources": resources}},
        entry=SimpleNamespace(unique_id="test"),
        last_update_success=True,
        client=AsyncMock(),
    )


def test_cloud_summary_uses_completed_timestamp_and_wh_scaling():
    c = coordinator(
        {
            "sessions": {
                "data": [
                    {
                        "stopTime": "2026-10-20 21:00:00",
                        "energy": 2000,
                        "cost": 0.5,
                        "currencyType": 1,
                    },
                    {
                        "stopTime": "2026-10-24 22:00:00",
                        "energy": 12500,
                        "duration": 7200,
                        "cost": 3.75,
                        "currencyType": 2,
                    },
                    {"stopTime": None, "energy": 99999},
                ]
            },
            "schedules": [],
        }
    )
    assert ResourceSensor(c, 1, "last_session_energy").native_value == 12.5
    assert ResourceSensor(c, 1, "last_session_duration").native_value == 7200
    cost = ResourceSensor(c, 1, "last_session_cost")
    assert cost.native_value == 3.75
    assert cost.extra_state_attributes == {"currency_id": 2, "source": "ChargerSync"}
    assert ResourceSensor(c, 1, "recent_session_count").native_value == 3
    assert ResourceSensor(c, 1, "schedule_count").native_value == 0


def test_failed_resources_never_become_zero_and_missing_sessions_stay_unknown():
    c = coordinator({})
    assert ResourceSensor(c, 1, "schedule_count").available is False
    assert ResourceSensor(c, 1, "last_session_energy").native_value is None
    c.data[1]["resources"] = {"sessions": []}
    assert ResourceSensor(c, 1, "last_session_energy").available
    assert ResourceSensor(c, 1, "last_session_energy").native_value is None
    c.data[1]["resources"]["sessions"] = [{"stopTime": "2026-10-24", "energy": "nan"}]
    assert ResourceSensor(c, 1, "last_session_energy").native_value is None


async def test_diagnostics_action_excludes_device_and_account_secrets():
    c = coordinator({"sessions": [{"secret": "private-history"}]})
    c.controllers = {1: SimpleNamespace(unsupported={"cable"})}
    c.data[1]["device"].update(pinCode="private-pin", sessionId="private-token")
    c.data[1]["remote_failure"] = {
        "stage": "cloud_login",
        "error": "ProtocolError",
        "payload": "private-token",
    }
    c.data[1]["settings_failures"] = {
        "active_mode": {"error": "ConfigurationUnavailableError", "result_code": 1}
    }
    result = await execute(
        c, 1, "get_data", SCHEMAS["get_data"]({"device_id": "test", "resource": "diagnostics"})
    )
    assert "private" not in str(result)
    assert result["result"]["unsupported"] == ["cable"]
    assert result["result"]["settings_failures"]["active_mode"]["result_code"] == 1


async def test_frontend_registers_route_without_preloading_before_ha(hass):
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
    from homeassistant.helpers.collection import ObservableCollection  # noqa: F401

    hass.config.components.add("frontend")
    hass.data[DATA_EXTRA_MODULE_URL] = set()
    http = SimpleNamespace(async_register_static_paths=AsyncMock())
    with patch.object(type(hass), "http", property(lambda self: http), create=True):
        await async_setup_frontend(hass)
        await async_setup_frontend(hass)
    http.async_register_static_paths.assert_awaited_once()
    paths = http.async_register_static_paths.call_args.args[0]
    assert paths[0].url_path == "/abb_chargersync/chargersync-card.js"
    assert not hass.data[DATA_EXTRA_MODULE_URL]


async def test_lovelace_resource_registered_once_without_changing_other_resources(hass):
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.components.lovelace.resources import ResourceStorageCollection

    from custom_components.abb_chargersync.const import VERSION
    from custom_components.abb_chargersync.frontend import CARD_PATH, async_register_card_resource

    config = SimpleNamespace(async_load=AsyncMock(return_value={}))
    resources = ResourceStorageCollection(hass, config)
    unrelated = await resources.async_create_item(
        {"url": "/local/other-card.js", "res_type": "module"}
    )
    hass.data[LOVELACE_DATA] = SimpleNamespace(resources=resources)
    await async_register_card_resource(hass)
    await async_register_card_resource(hass)
    items = resources.async_items()
    assert len(items) == 2
    assert unrelated in items
    assert any(
        item["url"] == f"{CARD_PATH}?v={VERSION}" and item["type"] == "module" for item in items
    )


async def test_lovelace_resource_upgrade_preserves_registration_id(hass):
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.components.lovelace.resources import ResourceStorageCollection

    from custom_components.abb_chargersync.const import VERSION
    from custom_components.abb_chargersync.frontend import CARD_PATH, async_register_card_resource

    config = SimpleNamespace(async_load=AsyncMock(return_value={}))
    resources = ResourceStorageCollection(hass, config)
    original = await resources.async_create_item({"url": f"{CARD_PATH}?v=old", "res_type": "js"})
    hass.data[LOVELACE_DATA] = SimpleNamespace(resources=resources)
    await async_register_card_resource(hass)
    assert resources.async_items() == [
        {"id": original["id"], "url": f"{CARD_PATH}?v={VERSION}", "type": "module"}
    ]


async def test_frontend_is_registered_before_first_cloud_refresh(hass):
    from homeassistant.exceptions import ConfigEntryNotReady
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.abb_chargersync import async_setup_entry
    from custom_components.abb_chargersync.const import DOMAIN

    order = []

    async def frontend_ready(hass):
        order.append("frontend")

    async def cloud_refresh():
        order.append("cloud")
        raise ConfigEntryNotReady("Cloud offline")

    entry = MockConfigEntry(domain=DOMAIN, data={"token": {}})
    entry.add_to_hass(hass)
    with (
        patch("custom_components.abb_chargersync.async_setup_frontend", side_effect=frontend_ready),
        patch(
            "custom_components.abb_chargersync.coordinator.ChargerSyncCoordinator.async_config_entry_first_refresh",
            side_effect=cloud_refresh,
        ),
    ):
        import pytest

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, entry)
    assert order == ["frontend", "cloud"]
