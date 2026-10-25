"""Constants from the ChargerSync 3.5.0 Android application."""

DOMAIN = "abb_chargersync"
VERSION = "0.2.1"
API_URL = "https://abb-user.chargedot.com/"
WS_URL = "wss://abb.api.chargedot.com:18971/ws/login"
APP_VERSION = "3.5.0"
# Public Android application's OAuth client, not a user's credentials.
CLIENT_ID = "3710400e-1c02-4175-84ea-40a227c0dcf6"
CLIENT_SECRET = "f1a6d022-8a8e-453c-862e-ba0d3c5b4521"
DEFAULT_INTERVAL = 30
REQUEST_TIMEOUT = 20
MODES = {"max_speed": 1, "eco_mix": 2, "solar": 3}
STATUSES = {
    0: "available",
    1: "plugged_in",
    2: "waiting",
    3: "reserved",
    4: "suspended_evse",
    5: "suspended_ev",
    6: "charging",
    7: "pausing",
    8: "finished",
    14: "unavailable",
    15: "faulted",
}
