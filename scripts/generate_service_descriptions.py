import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
# Direct script execution adds scripts/, so make the project package importable.
sys.path.insert(0, str(ROOT))

from custom_components.abb_chargersync.services import SCHEMAS  # noqa: E402


def field(name, selector, required=False, description=None):
    value = {"name": name, "required": required, "selector": selector}
    if description:
        value["description"] = description
    return value


text = {"text": {}}


def num(lo, hi):
    return {"number": {"min": lo, "max": hi, "mode": "box"}}


boolean = {"boolean": {}}


def select(options):
    return {"select": {"options": options}}


fields = {
    "name": field("Charger name", text, True),
    "device_id": field("Charger", {"device": {"integration": "abb_chargersync"}}, True),
    "resource": field(
        "Data",
        select(
            [
                "sessions",
                "trends",
                "schedules",
                "price",
                "auto_export",
                "firmware",
                "currencies",
                "load_limits",
                "log_info",
                "logs",
                "solar_offsets",
            ]
        ),
        True,
    ),
    "page": field("Page", num(0, 100000)),
    "limit": field("Page size / log count", num(1, 100)),
    "start_time": field(
        "Start time",
        text,
        False,
        "For schedules HH:MM; for history and exports use the API date/time format returned by get_data.",
    ),
    "end_time": field("End time", text),
    "card_number": field("Card filter", text),
    "company_only": field("Company-car sessions", boolean),
    "trend_type": field("Trend type", text),
    "log_from": field("First log serial", num(0, 4294967295)),
    "enabled": field("Enabled", boolean),
    "schedule_id": field("Schedule ID", num(0, 2147483647)),
    "settings": field("Settings", {"object": {}}, True),
    "ranges": field(
        "Time ranges",
        {"object": {}},
        True,
        "List of weekdays bitmask, from/to seconds after midnight and limit in amperes. Replaces the entire list, including country-specific limits.",
    ),
    "email": field("Recipient email", text),
    "format": field("Report format", select(["csv", "excel", "pdf"])),
    "session_id": field("Cloud session orderId", text, True),
    "company": field("Company-car session", boolean, True),
}
desc = {
    "set_solar_offsets": (
        "Update solar thresholds",
        "Patch Solar/Eco mix current offsets (0..5 A) and waiting times (0..120 s). Other values are preserved.",
    ),
    "update_charger": ("Rename charger", "Change the charger name in the ChargerSync cloud."),
    "get_data": (
        "Get cloud data",
        "Return sessions, statistics, schedules, tariffs, report settings, firmware packages or device diagnostics.",
    ),
    "create_schedule": ("Create charging schedule", "Create a cloud charging time window."),
    "update_schedule": (
        "Update charging schedule",
        "Update an existing schedule belonging to this charger.",
    ),
    "delete_schedule": ("Delete charging schedule", "Delete a schedule belonging to this charger."),
    "set_price": (
        "Update energy tariff",
        "Merge tariff fields into the current tariff, preserving other settings.",
    ),
    "set_auto_export": (
        "Update automatic reports",
        "Merge report settings into the current configuration. Cycle is 1, 3 or 6 months.",
    ),
    "export_sessions": (
        "Export charging sessions",
        "Request a report sent by ChargerSync to the supplied email address.",
    ),
    "set_company_session": (
        "Mark company-car session",
        "Change the company-car flag of a session in this charger’s recent history.",
    ),
    "replace_load_limits": (
        "Replace timed current limits",
        "Replace all current-limit time ranges; existing country-specific ranges are replaced too.",
    ),
    "refresh": ("Refresh cloud data", "Refresh cloud inventory, settings and remote status."),
}
services = {}
# Requiredness comes from the same schema that validates service calls.
for name, schema in SCHEMAS.items():
    fs = {}
    for marker in schema.schema:
        key = marker.schema if hasattr(marker, "schema") else marker
        value = dict(fields[key])
        value["required"] = type(marker).__name__ == "Required"
        fs[key] = value
    services[name] = {"name": desc[name][0], "description": desc[name][1], "fields": fs}
(ROOT / "custom_components/abb_chargersync/services.yaml").write_text(
    yaml.safe_dump(services, sort_keys=False, allow_unicode=True)
)
