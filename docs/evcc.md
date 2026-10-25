# EVCC through the Home Assistant API

Restart Home Assistant after installing the integration. In EVCC, add a
Home Assistant charger, connect your Home Assistant instance and provide a
Home Assistant long-lived access token through EVCC's credential setup.
Select the entities belonging to the same charger. Example entity IDs below
assume the charger is named Driveway; use the actual IDs from Home Assistant.

```yaml
chargers:
  - name: driveway
    type: template
    template: homeassistant
    uri: http://homeassistant.local:8123
    status: sensor.driveway_evcc_status
    enabled: switch.driveway_charging_enabled
    enable: switch.driveway_charging_enabled
    setMaxCurrent: number.driveway_charging_current_limit
    energy: sensor.driveway_charging_energy
```

`EVCC status` returns A (available), B (connected, waiting, suspended,
pausing or finished), or C (charging). Reserved, faulted, unavailable and
unrecognized statuses return unknown, so EVCC cannot mistake them for ready.

`Charging enabled` starts and stops sessions with the same commands as the
existing buttons. Its feedback comes from the charger: charging and suspended
session states are on; available, plugged in and finished are off. Waiting,
reserved, pausing, faults and unknown states have unknown enabled feedback.
The switch never assumes a successful command means the charger has changed
state. Offline entities become unavailable. Repeated commands are skipped only
when the observed state already matches the request.

This is session control, not a permanent authorization gate. The protocol does
not expose an independent persistent "charging allowed" flag. In particular,
starting while unplugged cannot promise that a future connection is authorized.
Verify start, stop, vehicle sleep/wake and reconnect with your charger before
leaving EVCC unattended. Unknown feedback needs investigation rather than a
locally remembered switch state.

Use Max speed mode and remove conflicting schedules/solar controllers in the
official app when EVCC should control charging. Current limits use whole amperes
from 6 A to the device maximum. Keep `milliamps` disabled. The default cloud
polling interval is 30 seconds; allow time for charger feedback.

The cumulative charging energy sensor is in kWh and has the coverage limitations
described in [Energy dashboard](energy-dashboard.md). Do not configure apparent
power (VA) as EVCC active power (W). Per-phase current and voltage sensors are
optional and only available when the charger supplies those measurements.
No phase-switching control is exposed.

EVCC communicates with Home Assistant locally, but this integration still
requires the ABB cloud for charger communication.

See the [EVCC Home Assistant charger documentation](https://docs.evcc.io/en/chargers/home-assistant-charger/)
for credential setup and optional parameters.
