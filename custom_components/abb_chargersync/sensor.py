"""Session and device sensors. Never present stale readings as live measurements."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import (
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfTime,
)

from .entity import ChargerSyncEntity, discover

PARALLEL_UPDATES = 0
SENSORS = {
    "status": ("Charging status", None, None, None),
    "session_energy": (
        "Session energy",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
    ),
    "solar_energy": (
        "Session solar energy",
        UnitOfEnergy.KILO_WATT_HOUR,
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL,
    ),
    "solar_percentage": ("Session solar share", "%", None, SensorStateClass.MEASUREMENT),
    "duration": (
        "Session duration",
        UnitOfTime.SECONDS,
        SensorDeviceClass.DURATION,
        SensorStateClass.MEASUREMENT,
    ),
    "apparent_power": (
        "Apparent power",
        "VA",
        SensorDeviceClass.APPARENT_POWER,
        SensorStateClass.MEASUREMENT,
    ),
    "fault_code": ("Fault code", None, None, None),
    "maximum_current": (
        "Maximum current",
        UnitOfElectricCurrent.AMPERE,
        SensorDeviceClass.CURRENT,
        None,
    ),
}
for phase in (1, 2, 3):
    SENSORS[f"voltage_l{phase}"] = (
        f"Voltage L{phase}",
        UnitOfElectricPotential.VOLT,
        SensorDeviceClass.VOLTAGE,
        SensorStateClass.MEASUREMENT,
    )
    SENSORS[f"current_l{phase}"] = (
        f"Current L{phase}",
        UnitOfElectricCurrent.AMPERE,
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
    )
    SENSORS[f"solar_current_l{phase}"] = (
        f"Solar current L{phase}",
        UnitOfElectricCurrent.AMPERE,
        SensorDeviceClass.CURRENT,
        SensorStateClass.MEASUREMENT,
    )


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(c, i, snapshot):
        for key in SENSORS:
            if key == "status" or key in snapshot.get("state", {}):
                yield ChargerSyncSensor(c, i, key)
        yield FirmwareSensor(c, i, "firmware", "Firmware", remote=False)
        if "latest-upgrade-packages" in snapshot.get("resources", {}):
            yield FirmwareAvailableSensor(
                c, i, "available_firmware", "Available firmware", remote=False
            )

    discover(entry, async_add_entities, factory)


class ChargerSyncSensor(ChargerSyncEntity, SensorEntity):
    def __init__(self, coordinator, device_id, key):
        name, unit, device_class, state_class = SENSORS[key]
        super().__init__(coordinator, device_id, key, name, required=key)
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if key == "status":
            self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self):
        return self.state_data.get(self.key)


class FirmwareSensor(ChargerSyncEntity, SensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        return self.snapshot.get("device", {}).get("softVersion")


class FirmwareAvailableSensor(FirmwareSensor):
    @property
    def native_value(self):
        packages = self.snapshot.get("resources", {}).get("latest-upgrade-packages")
        if not isinstance(packages, list):
            return None
        # Do not guess which of multiple hardware-specific packages is the latest.
        versions = sorted({p["softVersion"] for p in packages if p.get("softVersion")})
        return versions[0] if len(versions) == 1 else None
