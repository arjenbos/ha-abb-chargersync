"""Session and solar controls, excluding free-vending settings."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from .entity import ChargerSyncEntity, discover
from .evcc import SESSION_ENABLED

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(c, i, snapshot):
        yield ChargingEnabledSwitch(
            c, i, "charging_enabled", "Charging enabled", required="status_code"
        )
        for key, name in (
            ("solar_enabled", "Solar charging enabled"),
            ("ignore_eco_threshold", "Ignore Eco mix start-stop threshold"),
        ):
            if key in snapshot.get("state", {}):
                yield ChargerSyncSwitch(c, i, key, name, required=key)

    discover(entry, async_add_entities, factory)


class ChargerSyncSwitch(ChargerSyncEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self):
        return self.state_data.get(self.key)

    async def _set(self, enabled):
        if self.key == "ignore_eco_threshold":
            await self.run("ignore_threshold", enabled=enabled)
        else:
            await self.run("set_mode", mode=self.state_data["default_mode"], enabled=enabled)

    async def async_turn_on(self, **kwargs):
        await self._set(True)

    async def async_turn_off(self, **kwargs):
        await self._set(False)


class ChargingEnabledSwitch(ChargerSyncEntity, SwitchEntity):
    """Start/stop a session and report only observed authorization state."""

    _attr_icon = "mdi:ev-station"

    @property
    def is_on(self):
        return SESSION_ENABLED.get(self.state_data.get("status_code"))

    async def async_turn_on(self, **kwargs):
        if self.is_on is not True:
            await self.run("start")

    async def async_turn_off(self, **kwargs):
        if self.is_on is not False:
            await self.run("stop")
