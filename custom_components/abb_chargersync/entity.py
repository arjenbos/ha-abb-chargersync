"""Shared device entities and dynamic discovery after reconnect or account changes."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ChargerSyncCoordinator


class ChargerSyncEntity(CoordinatorEntity[ChargerSyncCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        device_id: int,
        key: str,
        name: str,
        *,
        remote: bool = True,
        required: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        self.key = key
        self.remote_required = remote
        self.required = required
        device = coordinator.data[device_id]["device"]
        self._attr_unique_id = f"{coordinator.entry.unique_id}_{device['deviceNumber']}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["deviceNumber"])},
            manufacturer="ABB",
            name=device.get("aliasNumber") or device["deviceNumber"],
            model=device.get("model") or device.get("hardwareModel"),
            sw_version=device.get("softVersion"),
            hw_version=device.get("hardwareVersion"),
        )

    @property
    def snapshot(self) -> dict:
        return self.coordinator.data.get(self.device_id, {})

    @property
    def state_data(self) -> dict:
        return self.snapshot.get("state", {})

    @property
    def available(self) -> bool:
        return (
            super().available
            and bool(self.snapshot)
            and (not self.remote_required or self.snapshot.get("remote_available", False))
            and (self.required is None or self.required in self.state_data)
        )

    async def run(self, operation, **kwargs) -> None:
        await self.coordinator.action(self.device_id, operation, **kwargs)


def discover(entry, async_add_entities, factory: Callable) -> None:
    """Add entities when capabilities first become available, including after initial offline setup."""
    coordinator = entry.runtime_data
    seen = set()

    @callback
    def update() -> None:
        entities = []
        for device_id, snapshot in coordinator.data.items():
            for entity in factory(coordinator, device_id, snapshot):
                if entity.unique_id not in seen:
                    seen.add(entity.unique_id)
                    entities.append(entity)
        if entities:
            async_add_entities(entities)

    update()
    entry.async_on_unload(coordinator.async_add_listener(update))
