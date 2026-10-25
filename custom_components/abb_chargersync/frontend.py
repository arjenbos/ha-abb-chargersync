"""Serve the bundled management card without copying files into www."""

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN, VERSION


async def async_setup_frontend(hass):
    """Register once across all configured ChargerSync accounts."""
    key = f"{DOMAIN}_frontend"
    if hass.data.get(key):
        return
    # Tests and headless HA installations need not load the frontend.
    if "frontend" not in hass.config.components:
        return
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/abb_chargersync/chargersync-card.js",
                str(Path(__file__).parent / "www/chargersync-card.js"),
                False,
            )
        ]
    )
    frontend.add_extra_js_url(hass, f"/abb_chargersync/chargersync-card.js?v={VERSION}")
    hass.data[key] = True
