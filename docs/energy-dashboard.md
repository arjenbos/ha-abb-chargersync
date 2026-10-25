# Energy dashboard

Use the **Charging energy** sensor for the charger's entry under **Settings →
Dashboards → Energy → Individual devices → Add device**. Select the sensor
belonging to your charger, for example `sensor.driveway_charging_energy`.

The integration provides `device_class: energy`, `state_class: total_increasing`
and `unit_of_measurement: kWh`. Leave Recorder enabled for this sensor. Once
Home Assistant has compiled its statistics, the Energy dashboard can display
the charger's consumption alongside your other devices. This may take a few
statistics intervals after the first valid measurement.

## What the counter measures

- The first valid charging measurement establishes the baseline. Energy already
  delivered before that measurement is not assigned to the current interval.
- Subsequent increases are accumulated. Session identifiers distinguish new
  sessions even when the new reading is higher than the previous session's reading.
- Missing readings, idle periods and connection failures leave the accumulated
  total unchanged. They do not insert zeros or reset the meter.
- The total and up to 32 recent session checkpoints are saved together through
  Home Assistant's restore-state mechanism, including integration unload/reload
  and normal Home Assistant restarts. Session checkpoints are not entity attributes.
- Repeated or lower readings for a known session are ignored until its previous
  high-water mark is exceeded.

This is an **observed-energy counter**, not the charger's lifetime meter. It does
not import historical sessions or recover energy from sessions that were entirely
missed while Home Assistant was stopped. Energy delivered after the final observed
reading of a session can also be missed. Cloud history is not merged into this
counter because its session identifiers have not been validated against the
remote protocol identifiers. Backfilled energy would also require assigning it to
the correct historical time intervals.

Where solar measurements are available, **Solar charging energy** uses the same
accounting method for the solar portion. That value is already included in
**Charging energy**. Do not add it as a second consuming device or as household
solar production: that would misrepresent the energy flow.

**Session energy**, **Session solar energy** and **Last session energy** remain
display values for individual sessions. They do not supply long-term sum statistics;
choose **Charging energy** for the Energy dashboard. Apparent power in VA is not
used to estimate active energy.
