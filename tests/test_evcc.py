"""EVCC API states must follow device feedback rather than service calls."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.abb_chargersync.sensor import EVCCStatusSensor
from custom_components.abb_chargersync.switch import ChargingEnabledSwitch


@pytest.mark.parametrize(
    ("code", "status", "enabled"),
    [
        (0, "A", False),
        (1, "B", False),
        (2, "B", None),
        (3, None, None),
        (4, "B", True),
        (5, "B", True),
        (6, "C", True),
        (7, "B", None),
        (8, "B", False),
        (14, None, None),
        (15, None, None),
        (99, None, None),
    ],
)
async def test_feedback(hass, code, status, enabled):
    coordinator = SimpleNamespace(
        hass=hass,
        last_update_success=True,
        entry=SimpleNamespace(unique_id="42"),
        data={
            1: {
                "device": {"deviceNumber": "TEST"},
                "remote_available": True,
                "state": {"status_code": code},
            }
        },
        action=AsyncMock(),
    )
    switch = ChargingEnabledSwitch(
        coordinator, 1, "charging_enabled", "Charging enabled", required="status_code"
    )
    sensor = EVCCStatusSensor(coordinator, 1, "evcc_status", "EVCC status", required="status_code")
    assert switch.is_on is enabled
    assert sensor.native_value == status
    await switch.async_turn_on()
    if enabled is not True:
        coordinator.action.assert_awaited_once_with(1, "start")
    else:
        coordinator.action.assert_not_awaited()
    assert switch.is_on is enabled
    coordinator.action.reset_mock()
    await switch.async_turn_off()
    if enabled is not False:
        coordinator.action.assert_awaited_once_with(1, "stop")
    else:
        coordinator.action.assert_not_awaited()
    assert switch.is_on is enabled
    coordinator.data[1]["remote_available"] = False
    assert not switch.available
    assert not sensor.available
