"""Cloud charging commands."""

from homeassistant.components.button import ButtonEntity

from .entity import ChargerSyncEntity, discover

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(c, i, snapshot):
        yield ChargerSyncButton(c, i, "start", "Start charging")
        yield ChargerSyncButton(c, i, "stop", "Stop charging")
        yield ChargerSyncButton(c, i, "skip_delay", "Skip charging delay")

    discover(entry, async_add_entities, factory)


class ChargerSyncButton(ChargerSyncEntity, ButtonEntity):
    _attr_icon = "mdi:ev-station"

    async def async_press(self):
        await self.run(self.key)
