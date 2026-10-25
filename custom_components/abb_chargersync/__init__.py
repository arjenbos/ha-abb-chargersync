"""ABB ChargerSync cloud integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ChargerSyncClient
from .coordinator import ChargerSyncCoordinator
from .frontend import async_setup_frontend
from .services import async_register_services

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.LOCK,
]
type ChargerSyncConfigEntry = ConfigEntry[ChargerSyncCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Publish frontend assets before any cloud-dependent entry refresh."""
    await async_setup_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ChargerSyncConfigEntry) -> bool:
    await async_setup_frontend(hass)

    def save_token(token: dict) -> None:
        hass.config_entries.async_update_entry(entry, data={**entry.data, "token": token})

    client = ChargerSyncClient(async_get_clientsession(hass), entry.data["token"], save_token)
    coordinator = ChargerSyncCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        async_register_services(hass)
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.async_close()
        raise
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ChargerSyncConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_shutdown()
        await entry.runtime_data.async_close()
        return True
    return False


async def async_reload_entry(hass: HomeAssistant, entry: ChargerSyncConfigEntry) -> None:
    if dict(entry.options) != entry.runtime_data.options_snapshot:
        await hass.config_entries.async_reload(entry.entry_id)
