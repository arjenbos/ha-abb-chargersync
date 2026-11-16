"""Charging cable lock, not RFID or account access management."""

import re

from homeassistant.components.lock import LockEntity
from homeassistant.exceptions import HomeAssistantError

from .entity import ChargerSyncEntity, discover

PARALLEL_UPDATES = 0


def _version(value) -> tuple[int, ...]:
    """Numeric firmware version, like ChargerCapabilitiesUtils.compareVersions."""
    return tuple(int(part) for part in re.findall(r"\d+", str(value or ""))[:3]) or (0,)


def _capable(device: dict, minimum: tuple[int, ...]) -> bool:
    """Mirror the app's socket-outlet and firmware gates for cable release and locking.

    Missing outlet or firmware fields keep the entity: a readable cable state already
    shows a lock. Only reported tethered outlets or older firmware disable it.
    """
    outlet = device.get("outlet")
    if outlet is not None and "socket" not in str(outlet):
        return False
    if device.get("productType") == 1 or not device.get("softVersion"):
        return True
    return _version(device.get("softVersion")) >= minimum


def release_supported(device: dict) -> bool:
    """isForceCableRemovingSupported: socket outlet, FX device or firmware 1.6.8+."""
    return _capable(device, (1, 6, 8))


def lock_supported(device: dict) -> bool:
    """isForceCableLockSupported: as above with firmware 1.8.2+ (app feature flag unknown)."""
    return _capable(device, (1, 8, 2))


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(c, i, snapshot):
        if "cable_locked" in snapshot.get("state", {}) and release_supported(snapshot["device"]):
            yield ChargerSyncLock(c, i, "cable_locked", "Charging cable", required="cable_locked")

    discover(entry, async_add_entities, factory)


class ChargerSyncLock(ChargerSyncEntity, LockEntity):
    @property
    def is_locked(self):
        return self.state_data.get("cable_locked")

    async def async_lock(self, **kwargs):
        if not lock_supported(self.snapshot.get("device", {})):
            raise HomeAssistantError("This charger's firmware does not support locking the cable")
        await self.run("lock")

    async def async_unlock(self, **kwargs):
        await self.run("unlock")
