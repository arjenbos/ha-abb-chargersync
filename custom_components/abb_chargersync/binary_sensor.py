"""Account connectivity and remote charging indicators."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory

from .entity import ChargerSyncEntity, discover

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(c, i, snapshot):
        yield ChargerSyncBinarySensor(c, i, "cloud_online", "Cloud online", remote=False)
        yield ChargerSyncBinarySensor(c, i, "remote_connected", "Remote connected", remote=False)
        yield ChargerSyncBinarySensor(c, i, "charging", "Charging", required="status_code")
        yield ChargerSyncBinarySensor(c, i, "fault", "Fault", required="status_code")

    discover(entry, async_add_entities, factory)


class ChargerSyncBinarySensor(ChargerSyncEntity, BinarySensorEntity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.key in ("cloud_online", "remote_connected"):
            self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        elif self.key == "fault":
            self._attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self):
        if self.key == "cloud_online":
            value = self.snapshot.get("device", {}).get("online")
            return None if value is None else value == 1
        if self.key == "remote_connected":
            return self.snapshot.get("remote_available", False)
        code = self.state_data.get("status_code")
        return None if code is None else code == (6 if self.key == "charging" else 15)
