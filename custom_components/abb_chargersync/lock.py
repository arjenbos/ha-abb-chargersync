"""Charging cable lock, not RFID or account access management."""

from homeassistant.components.lock import LockEntity

from .entity import ChargerSyncEntity, discover

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(c, i, snapshot):
        if "cable_locked" in snapshot.get("state", {}):
            yield ChargerSyncLock(c, i, "cable_locked", "Charging cable", required="cable_locked")

    discover(entry, async_add_entities, factory)


class ChargerSyncLock(ChargerSyncEntity, LockEntity):
    @property
    def is_locked(self):
        return self.state_data.get("cable_locked")

    async def async_lock(self, **kwargs):
        await self.run("lock")

    async def async_unlock(self, **kwargs):
        await self.run("unlock")
