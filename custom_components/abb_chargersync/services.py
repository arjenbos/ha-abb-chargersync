"""Validated cloud actions for schedules, reports, tariffs and device diagnostics."""

from __future__ import annotations

import struct

import probatio as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .api import AuthenticationError, ChargerSyncError
from .const import DOMAIN
from .protocol import SOLAR_OFFSETS, ProtocolError, parse_limits, parse_solar_offsets

DEVICE = {vol.Required("device_id"): cv.string}
TIME = vol.Match(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
PRICE_FIELDS = {
    "averagePrice",
    "currencyType",
    "midPeakEt",
    "midPeakPrice",
    "midPeakSt",
    "offPeakEt",
    "offPeakPrice",
    "offPeakSt",
    "onPeakEt",
    "onPeakPrice",
    "onPeakSt",
}
PRICE_SCHEMA = vol.Schema(
    {
        **{
            vol.Optional(k): vol.All(vol.Coerce(float), vol.Range(min=0))
            for k in ("averagePrice", "midPeakPrice", "offPeakPrice", "onPeakPrice")
        },
        **{
            vol.Optional(k): TIME
            for k in ("midPeakEt", "midPeakSt", "offPeakEt", "offPeakSt", "onPeakEt", "onPeakSt")
        },
        vol.Optional("currencyType"): cv.positive_int,
    }
)
AUTO_FIELDS = {"enabled", "format", "cycle", "email", "cardNumber", "isCompanyCarSession"}
AUTO_SCHEMA = vol.Schema(
    {
        vol.Required("enabled"): cv.boolean,
        vol.Optional("format"): vol.In(["csv", "excel", "pdf"]),
        vol.Optional("cycle"): vol.In([1, 3, 6]),
        vol.Optional("email"): cv.string,
        vol.Optional("cardNumber"): cv.string,
        vol.Optional("isCompanyCarSession"): cv.boolean,
    }
)
RANGE_SCHEMA = vol.Schema(
    {
        vol.Required("weekdays"): vol.All(vol.Coerce(int), vol.Range(min=1, max=127)),
        vol.Required("from"): vol.All(vol.Coerce(int), vol.Range(min=0, max=86399)),
        vol.Required("to"): vol.All(vol.Coerce(int), vol.Range(min=1, max=86400)),
        vol.Required("limit"): vol.All(vol.Coerce(int), vol.Range(min=0, max=255)),
    }
)
SCHEMAS = {
    "set_solar_offsets": vol.Schema(
        {
            **DEVICE,
            vol.Required("settings"): vol.Schema(
                {
                    vol.Optional(k): vol.All(vol.Coerce(float), vol.Range(min=0, max=5))
                    if k.endswith("current")
                    else vol.All(vol.Coerce(int), vol.Range(min=0, max=120))
                    for k in SOLAR_OFFSETS
                }
            ),
        }
    ),
    "update_charger": vol.Schema(
        {**DEVICE, vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=100))}
    ),
    "get_data": vol.Schema(
        {
            **DEVICE,
            vol.Required("resource"): vol.In(
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
                    "diagnostics",
                ]
            ),
            vol.Optional("page", default=0): cv.positive_int,
            vol.Optional("limit", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
            vol.Optional("start_time"): cv.string,
            vol.Optional("end_time"): cv.string,
            vol.Optional("card_number"): cv.string,
            vol.Optional("company_only"): cv.boolean,
            vol.Optional("trend_type"): cv.string,
            vol.Optional("log_from", default=0): cv.positive_int,
        }
    ),
    "create_schedule": vol.Schema(
        {
            **DEVICE,
            vol.Required("start_time"): TIME,
            vol.Required("end_time"): TIME,
            vol.Optional("enabled", default=True): cv.boolean,
        }
    ),
    "update_schedule": vol.Schema(
        {
            **DEVICE,
            vol.Required("schedule_id"): cv.positive_int,
            vol.Required("start_time"): TIME,
            vol.Required("end_time"): TIME,
            vol.Required("enabled"): cv.boolean,
        }
    ),
    "delete_schedule": vol.Schema({**DEVICE, vol.Required("schedule_id"): cv.positive_int}),
    "set_price": vol.Schema({**DEVICE, vol.Required("settings"): PRICE_SCHEMA}),
    "set_auto_export": vol.Schema({**DEVICE, vol.Required("settings"): AUTO_SCHEMA}),
    "export_sessions": vol.Schema(
        {
            **DEVICE,
            vol.Required("email"): cv.string,
            vol.Required("format"): vol.In(["csv", "excel", "pdf"]),
            vol.Required("start_time"): cv.string,
            vol.Required("end_time"): cv.string,
            vol.Optional("card_number"): cv.string,
            vol.Optional("company_only"): cv.boolean,
        }
    ),
    "set_company_session": vol.Schema(
        {**DEVICE, vol.Required("session_id"): cv.string, vol.Required("company"): cv.boolean}
    ),
    "replace_load_limits": vol.Schema(
        {
            **DEVICE,
            vol.Required("ranges"): vol.All([RANGE_SCHEMA], vol.Length(max=50)),
            vol.Optional("enabled", default=True): cv.boolean,
        }
    ),
    "refresh": vol.Schema(DEVICE),
}


def resolve(hass: HomeAssistant, device_id: str):
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError("Unknown Home Assistant device")
    numbers = {identifier for domain, identifier in device.identifiers if domain == DOMAIN}
    matches = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state != ConfigEntryState.LOADED or entry.entry_id not in device.config_entries:
            continue
        for charger_id, snapshot in entry.runtime_data.data.items():
            if snapshot["device"]["deviceNumber"] in numbers:
                matches.append((entry.runtime_data, charger_id))
    if len(matches) != 1:
        raise ServiceValidationError("Select a ChargerSync device with one loaded account")
    return matches[0]


async def execute(c, charger_id: int, service: str, data: dict):
    """Execute against a resolved account and linked device only."""
    client = c.client
    result = None
    if service == "get_data":
        resource = data["resource"]
        if resource == "diagnostics":
            snapshot = c.data[charger_id]
            result = {
                "model": snapshot["device"].get("model"),
                "firmware": snapshot["device"].get("softVersion"),
                "cloud_online": snapshot["device"].get("online"),
                "remote_available": snapshot.get("remote_available", False),
                "state_fields": sorted(snapshot.get("state", {})),
                "resources": sorted(snapshot.get("resources", {})),
                "unsupported": sorted(c.controllers[charger_id].unsupported),
                "settings_failures": snapshot.get("settings_failures", {}),
                "remote_failure": {
                    k: v
                    for k, v in snapshot.get("remote_failure", {}).items()
                    if k in {"stage", "error", "http_status"}
                },
            }
        elif resource == "solar_offsets":
            result = parse_solar_offsets(
                await c.controllers[charger_id].remote.query_configuration(12)
            )
        elif resource == "currencies":
            result = await client.currencies()
        elif resource == "load_limits":
            result = parse_limits(await c.controllers[charger_id].remote.command(164, b"\0"))
        elif resource in ("log_info", "logs"):
            remote = c.controllers[charger_id].remote
            raw = await remote.command(
                188 if resource == "log_info" else 189,
                b""
                if resource == "log_info"
                else struct.pack("<IB", data["log_from"], min(data["limit"], 50)),
            )
            if resource == "log_info":
                if len(raw) != 10:
                    raise ProtocolError("Invalid log metadata")
                first, last, count = struct.unpack("<IIH", raw)
                result = {"first": first, "last": last, "count": count}
            else:
                if len(raw) % 13:
                    raise ProtocolError("Invalid log records")
                result = [
                    {"serial": v[0], "timestamp": v[1], "type": v[2], "code": v[3], "detail": v[4]}
                    for v in struct.iter_unpack("<IIBHH", raw)
                ]
        else:
            params = {}
            if resource in ("sessions", "trends"):
                for key, api_key in (
                    ("start_time", "startTime"),
                    ("end_time", "endTime"),
                    ("card_number", "cardNumber"),
                ):
                    if key in data:
                        params[api_key] = data[key]
                if "company_only" in data:
                    params["isCompanyCarSession"] = int(data["company_only"])
                if resource == "sessions":
                    params.update(page=data["page"], per_page=data["limit"])
                elif "trend_type" in data:
                    params["type"] = data["trend_type"]
            path = {
                "auto_export": "sessions/auto-export",
                "firmware": "latest-upgrade-packages",
            }.get(resource, resource)
            result = await client.read(charger_id, path, **params)
        return {"result": result}
    if service == "set_solar_offsets":
        await c.action(charger_id, "set_solar_offsets", settings=data["settings"])
        return {"result": None}
    if service == "update_charger":
        result = await client.rename(charger_id, data["name"])
    elif service in ("create_schedule", "update_schedule", "delete_schedule"):
        body = {
            "startTime": data.get("start_time"),
            "endTime": data.get("end_time"),
            "open": int(data.get("enabled", True)),
        }
        if service != "create_schedule":
            schedules = await client.read(charger_id, "schedules")
            if not isinstance(schedules, list) or not any(
                str(s.get("id")) == str(data["schedule_id"]) for s in schedules
            ):
                raise ServiceValidationError("Schedule does not belong to this charger")
        if service == "create_schedule":
            result = await client.create_schedule(charger_id, body)
        elif service == "update_schedule":
            result = await client.update_schedule(data["schedule_id"], body)
        else:
            result = await client.delete_schedule(data["schedule_id"])
    elif service == "set_price":
        current = await client.read(charger_id, "price")
        if not isinstance(current, dict):
            raise ProtocolError("Cannot preserve tariff settings")
        body = {k: v for k, v in current.items() if k in PRICE_FIELDS}
        body.update({k: str(v) if k.endswith("Price") else v for k, v in data["settings"].items()})
        result = await client.set_price(charger_id, body)
    elif service == "set_auto_export":
        current = await client.read(charger_id, "sessions/auto-export")
        if not isinstance(current, dict):
            raise ProtocolError("Cannot preserve report settings")
        body = {k: v for k, v in current.items() if k in AUTO_FIELDS}
        body.update(data["settings"])
        result = await client.set_auto_export(charger_id, body)
    elif service == "export_sessions":
        body = {
            "email": data["email"],
            "format": data["format"],
            "startTime": data["start_time"],
            "endTime": data["end_time"],
        }
        if "card_number" in data:
            body["cardNumber"] = data["card_number"]
        if "company_only" in data:
            body["isCompanyCarSession"] = data["company_only"]
        result = await client.export_sessions(charger_id, body)
    elif service == "set_company_session":
        # Session IDs are cloud-global; enforce charger ownership, bounded pagination.
        found = False
        for page in range(20):
            history = await client.read(charger_id, "sessions", page=page, per_page=100)
            sessions = history.get("data", []) if isinstance(history, dict) else history
            if not isinstance(sessions, list):
                raise ProtocolError("Invalid session history")
            if any(str(s.get("orderId")) == data["session_id"] for s in sessions):
                found = True
                break
            if len(sessions) < 100:
                break
        if not found:
            raise ServiceValidationError("Session not found in this charger's recent history")
        result = await client.set_company_session(data["session_id"], data["company"])
    elif service == "replace_load_limits":
        await c.action(charger_id, "replace_limits", ranges=data["ranges"], enabled=data["enabled"])
        return {"result": None}
    c._rest_updated = 0
    await c.async_request_refresh()
    return {"result": result}


@callback
def async_register_services(hass: HomeAssistant) -> None:
    async def handle(call: ServiceCall):
        c, charger_id = resolve(hass, call.data["device_id"])
        try:
            return await execute(c, charger_id, call.service, dict(call.data))
        except AuthenticationError as err:
            c.entry.async_start_reauth(hass)
            raise HomeAssistantError("Sign in again to ChargerSync") from err
        except (ChargerSyncError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err

    for name, schema in SCHEMAS.items():
        if not hass.services.has_service(DOMAIN, name):
            hass.services.async_register(
                DOMAIN,
                name,
                handle,
                schema=schema,
                supports_response=SupportsResponse.ONLY
                if name == "get_data"
                else SupportsResponse.OPTIONAL,
            )
