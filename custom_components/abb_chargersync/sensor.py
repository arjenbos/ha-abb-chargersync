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
        for key in RESOURCE_SENSORS:
            yield ResourceSensor(c, i, key)

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


RESOURCE_SENSORS = {
    "schedule_count": ("Charging schedules", "schedules", None, None),
    "recent_session_count": ("Recent sessions", "sessions", None, None),
    "last_session_energy": ("Last session energy", "sessions", "energy", "kWh"),
    "last_session_duration": ("Last session duration", "sessions", "duration", "s"),
    "last_session_cost": ("Last session cost", "sessions", "cost", None),
}


class ResourceSensor(ChargerSyncEntity, SensorEntity):
    """Small cloud summaries; history and personal information stay out of attributes."""

    def __init__(self, coordinator, device_id, key):
        name, self.resource, self.field, unit = RESOURCE_SENSORS[key]
        super().__init__(coordinator, device_id, key, name, remote=False)
        self._attr_native_unit_of_measurement = unit
        if key == "last_session_energy":
            self._attr_device_class = SensorDeviceClass.ENERGY
        elif key == "last_session_duration":
            self._attr_device_class = SensorDeviceClass.DURATION

    @property
    def records(self):
        value = self.snapshot.get("resources", {}).get(self.resource)
        if isinstance(value, dict):
            value = value.get("data")
        return (
            value if isinstance(value, list) and all(isinstance(r, dict) for r in value) else None
        )

    @property
    def available(self):
        return super().available and self.records is not None

    @property
    def native_value(self):
        records = self.records
        if records is None:
            return None
        if self.field is None:
            return len(records)
        # Select by the observed API timestamp, without assuming server ordering.
        completed = [r for r in records if r.get("stopTime")]
        last = max(completed, key=lambda r: str(r["stopTime"]), default={})
        value = last.get(self.field)
        try:
            return float(value) if value is not None else None
        except TypeError, ValueError:
            return None

    @property
    def extra_state_attributes(self):
        if self.key == "recent_session_count":
            return {"scope": "Most recent page, up to 20 sessions"}
        if self.key == "last_session_cost":
            completed = [r for r in self.records or [] if r.get("stopTime")]
            last = max(completed, key=lambda r: str(r["stopTime"]), default={})
            return {"currency_id": last.get("currencyType"), "source": "ChargerSync"}
        return None
