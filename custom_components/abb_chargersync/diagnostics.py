"""Allowlisted diagnostics: exclude credentials, identifiers and session history entirely."""

from .const import DOMAIN


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    return {
        "integration": DOMAIN,
        "version": "0.1.0",
        "scan_interval": entry.options.get("scan_interval", 30),
        "devices": [
            {
                "model": s["device"].get("model"),
                "firmware": s["device"].get("softVersion"),
                "remote_available": s.get("remote_available", False),
                "state_fields": sorted(s.get("state", {})),
                "resource_names": sorted(s.get("resources", {})),
                "unsupported": sorted(coordinator.controllers[i].unsupported),
            }
            for i, s in coordinator.data.items()
        ],
    }
