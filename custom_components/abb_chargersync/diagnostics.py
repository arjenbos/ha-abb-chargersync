"""Allowlisted diagnostics: exclude credentials, identifiers and session history entirely."""

from .const import DOMAIN, VERSION


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    return {
        "integration": DOMAIN,
        "version": VERSION,
        "scan_interval": entry.options.get("scan_interval", 30),
        "devices": [
            {
                "model": s["device"].get("model"),
                "firmware": s["device"].get("softVersion"),
                "cloud_online": s["device"].get("online"),
                "remote_available": s.get("remote_available", False),
                "remote_failure": {
                    key: value
                    for key, value in s.get("remote_failure", {}).items()
                    if key in {"stage", "error", "http_status"}
                },
                "settings_failures": {
                    name: {
                        key: value
                        for key, value in failure.items()
                        if key
                        in {"stage", "error", "http_status", "response_length", "result_code"}
                    }
                    for name, failure in s.get("settings_failures", {}).items()
                },
                "state_fields": sorted(s.get("state", {})),
                "resource_names": sorted(s.get("resources", {})),
                "unsupported": sorted(coordinator.controllers[i].unsupported),
            }
            for i, s in coordinator.data.items()
        ],
    }
