"""Default and active-session energy modes."""

from homeassistant.components.select import SelectEntity

from .const import MODES
from .entity import ChargerSyncEntity, discover

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(c, i, snapshot):
        for key, name in (
            ("active_mode", "Active charging mode"),
            ("default_mode", "Default charging mode"),
        ):
            if key in snapshot.get("state", {}):
                yield ChargerSyncSelect(c, i, key, name, required=key)

    discover(entry, async_add_entities, factory)


class ChargerSyncSelect(ChargerSyncEntity, SelectEntity):
    _attr_options = list(MODES)

    @property
    def current_option(self):
        return self.state_data.get(self.key)

    async def async_select_option(self, option):
        await self.run("set_mode", mode=option, active=self.key == "active_mode")
