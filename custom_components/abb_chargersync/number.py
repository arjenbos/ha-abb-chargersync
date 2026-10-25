"""Current limit and Eco mix minimum current."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfElectricCurrent

from .entity import ChargerSyncEntity, discover

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    def factory(c, i, snapshot):
        state = snapshot.get("state", {})
        if "current_limit" in state and state.get("maximum_current", 0) >= 6:
            yield ChargerSyncNumber(
                c, i, "current_limit", "Charging current limit", required="current_limit"
            )
        if "default_mode" in state:
            yield ChargerSyncNumber(
                c, i, "solar_min_current", "Eco mix minimum current", required="solar_min_current"
            )

    discover(entry, async_add_entities, factory)


class ChargerSyncNumber(ChargerSyncEntity, NumberEntity):
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    @property
    def available(self):
        return super().available and (
            self.key != "solar_min_current" or self.state_data.get("default_mode") == "eco_mix"
        )

    @property
    def native_min_value(self):
        return 6 if self.key == "current_limit" else 0

    @property
    def native_max_value(self):
        return self.state_data.get("maximum_current", 6) if self.key == "current_limit" else 6

    @property
    def native_value(self):
        return self.state_data.get(self.key)

    async def async_set_native_value(self, value):
        if int(value) != value:
            from homeassistant.exceptions import HomeAssistantError

            raise HomeAssistantError("Only whole amperes are supported")
        if self.key == "current_limit":
            await self.run("set_current", current=int(value))
        else:
            await self.run("set_mode", mode="eco_mix", minimum=int(value))
