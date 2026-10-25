"""Validate dashboard binding and customization against real HA-created entity IDs."""

import re
from unittest.mock import patch

import pytest
import yaml
from pytest_homeassistant_custom_component.common import MockConfigEntry

from scripts.generate_dashboard import generate


def test_customized_entities_include_templates_and_action_targets():
    config = generate(
        "driveway",
        "Driveway charger",
        {
            "sensor.charger_charging_status": "sensor.ev_status",
            "button.charger_start_charging": "button.ev_start",
        },
    )
    serialized = yaml.safe_dump(config)
    assert ".charger_" not in serialized
    assert "CHARGER_DISPLAY_NAME" not in serialized
    assert "sensor.ev_status" in config["views"][0]["header"]["card"]["content"]
    assert "button.ev_start" in serialized
    assert "number.driveway_charging_current_limit" in serialized
    assert len(config["views"]) == 3


@pytest.mark.parametrize(
    "prefix,name,mapping",
    [
        ("Driveway", "Home charger", {}),
        ("driveway", "{{ template }}", {}),
        ("driveway", "Home charger", {"sensor.charger_typo": "sensor.other"}),
        ("driveway", "Home charger", {"button.charger_start_charging": "lock.front_door"}),
    ],
)
def test_invalid_customization_rejected(prefix, name, mapping):
    with pytest.raises(ValueError):
        generate(prefix, name, mapping)


async def test_every_dashboard_entity_matches_the_integration(hass):
    from custom_components.abb_chargersync.const import DOMAIN
    from custom_components.abb_chargersync.sensor import SENSORS

    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="42", data={"username": "example@example.com", "token": {}}
    )
    entry.add_to_hass(hass)
    device = {"id": 1, "deviceNumber": "EXAMPLE", "aliasNumber": "Driveway", "online": 1}
    state = {key: 1 for key in SENSORS}
    state.update(status="charging", status_code=6)
    settings = {
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
    with (
        patch(
            "custom_components.abb_chargersync.api.ChargerSyncClient.devices", return_value=[device]
        ),
        patch("custom_components.abb_chargersync.api.ChargerSyncClient.read", return_value=[]),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.status",
            return_value=state,
        ),
        patch(
            "custom_components.abb_chargersync.controller.ChargerController.settings",
            return_value=settings,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        serialized = yaml.safe_dump(generate("driveway", "Driveway charger"))
        referenced = set(
            re.findall(
                r"\b(?:sensor|binary_sensor|button|number|select|switch|lock)\.driveway_[a-z0-9_]+",
                serialized,
            )
        )
        assert referenced
        assert referenced <= set(hass.states.async_entity_ids())
        await hass.config_entries.async_unload(entry.entry_id)
