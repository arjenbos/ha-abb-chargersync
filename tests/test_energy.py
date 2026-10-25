"""Energy accounting across sessions, connection gaps and Home Assistant restores."""

from unittest.mock import patch

import pytest
from homeassistant.core import State
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.abb_chargersync.const import DOMAIN
from custom_components.abb_chargersync.energy import EnergyCounter


def test_session_changes_even_when_new_session_reading_is_higher():
    counter = EnergyCounter()
    counter.update("first", 10)
    assert counter.total == 0
    counter.update("first", 12)
    assert counter.total == 2
    counter.update("second", 15)
    assert counter.total == 17
    counter.update("second", 16)
    assert counter.total == 18
    counter.update("third", 0)
    counter.update("third", 0.5)
    assert counter.total == 18.5


def test_duplicates_lower_readings_and_previous_sessions_do_not_double_count():
    counter = EnergyCounter()
    counter.update("first", 0)
    counter.update("first", 5)
    counter.update("first", 5)
    counter.update("first", 4.9)
    assert counter.total == 5
    counter.update("second", 1)
    counter.update("first", 5)
    assert counter.total == 6
    counter.update("second", 2)
    assert counter.total == 7


@pytest.mark.parametrize("value", [None, -1, float("nan"), float("inf"), True, "2"])
def test_invalid_measurements_never_change_the_counter(value):
    counter = EnergyCounter()
    counter.update("first", value)
    assert not counter.initialized
    counter.update("first", 0)
    counter.update("first", 1)
    counter.update("first", value)
    counter.update(None, 100)
    assert counter.total == 1


def test_restore_continues_same_session_without_double_counting():
    counter = EnergyCounter()
    counter.update("first", 2)
    counter.update("first", 5)
    restored = EnergyCounter()
    restored.restore(counter.as_dict())
    restored.update("first", 5.5)
    assert restored.total == 3.5
    restored.update("second", 2)
    assert restored.total == 5.5
    for i in range(40):
        restored.update(str(i), 0)
    assert len(restored.sessions) == 32


@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        {"version": 1, "total": -1, "sessions": {"x": 2}},
        {"version": 1, "total": 1, "sessions": {"x": float("nan")}},
    ],
)
def test_invalid_restore_data_is_not_used(data):
    counter = EnergyCounter()
    counter.restore(data)
    assert not counter.initialized


async def test_energy_entity_restores_updates_and_retains_total_when_idle(hass):
    entity_id = "sensor.driveway_charging_energy"
    counter = EnergyCounter()
    counter.update("ongoing", 2)
    counter.update("ongoing", 5)
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State(entity_id, "3"),
                {
                    "native_value": 3,
                    "native_unit_of_measurement": "kWh",
                    "counter": counter.as_dict(),
                },
            )
        ],
    )
    entry = MockConfigEntry(domain=DOMAIN, unique_id="42", data={"token": {}})
    entry.add_to_hass(hass)
    device = {"id": 1, "deviceNumber": "TEST", "aliasNumber": "Driveway", "online": 1}
    state = {
        "status": "charging",
        "status_code": 6,
        "session_id": "ongoing",
        "session_energy": 5.5,
        "solar_energy": 1,
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
            return_value={},
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        value = hass.states.get(entity_id)
        assert value.state == "3.5"
        assert value.attributes["device_class"] == "energy"
        assert value.attributes["state_class"] == "total_increasing"
        assert value.attributes["unit_of_measurement"] == "kWh"
        assert "state_class" not in hass.states.get("sensor.driveway_session_energy").attributes
        c = entry.runtime_data
        snapshot = c.data[1]
        c.async_set_updated_data({1: {**snapshot, "remote_available": False, "state": {}}})
        assert hass.states.get(entity_id).state == "3.5"
        c.async_set_updated_data({1: {**snapshot, "state": {"status": "waiting"}}})
        assert hass.states.get(entity_id).state == "3.5"
        c.async_set_updated_data(
            {1: {**snapshot, "state": {**state, "session_id": "new", "session_energy": 10}}}
        )
        assert hass.states.get(entity_id).state == "13.5"
        # Actual entity unload/reload exercises HA's extra restore-state lifecycle.
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "13.5"
        assert await hass.config_entries.async_unload(entry.entry_id)
