"""Serve the bundled management card without copying files into www."""

import asyncio
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection

from .const import DOMAIN, VERSION

CARD_PATH = "/abb_chargersync/chargersync-card.js"


async def async_register_card_resource(hass):
    """Make Lovelace await the module before creating the custom element."""
    if (lovelace := hass.data.get(LOVELACE_DATA)) is None:
        return
    resources = lovelace.resources
    if not isinstance(resources, ResourceStorageCollection):
        # YAML-owned resources remain user managed; the extra module is the fallback.
        return
    await resources.async_get_info()
    url = f"{CARD_PATH}?v={VERSION}"
    existing = next(
        (item for item in resources.async_items() if item["url"].split("?")[0] == CARD_PATH),
        None,
    )
    if existing is None:
        await resources.async_create_item({"url": url, "res_type": "module"})
    elif existing["url"] != url or existing["type"] != "module":
        await resources.async_update_item(existing["id"], {"url": url, "res_type": "module"})


async def async_setup_frontend(hass):
    """Register once across all configured ChargerSync accounts."""
    key = f"{DOMAIN}_frontend"
    # Tests and headless HA installations need not load the frontend.
    if "frontend" not in hass.config.components:
        return
    lock = hass.data.setdefault(f"{key}_lock", asyncio.Lock())
    async with lock:
        if not hass.data.get(key):
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        CARD_PATH,
                        str(Path(__file__).parent / "www/chargersync-card.js"),
                        False,
                    )
                ]
            )
            frontend.add_extra_js_url(hass, f"{CARD_PATH}?v={VERSION}")
            hass.data[key] = True
        await async_register_card_resource(hass)
