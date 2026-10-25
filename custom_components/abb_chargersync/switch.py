"""Solar controls, excluding free-vending/access authorization settings."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory

from .entity import ChargerSyncEntity, discover

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(c, i, snapshot):
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
