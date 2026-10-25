# Actions and parameters

Every action uses `device_id` from Home Assistant's device registry, not the numeric ABB device ID. Use the device picker in Developer tools → Actions. Queries return `{"result": ...}`.

## History and statistics

```yaml
action: abb_chargersync.get_data
data:
  device_id: REPLACE_WITH_HA_DEVICE_ID
  resource: sessions
  page: 0
  limit: 20
response_variable: charging_history
```

`resource` accepts `sessions`, `trends`, `schedules`, `price`, `auto_export`, `firmware`, `currencies`, `load_limits`, `solar_offsets`, `log_info`, and `logs`. The integration never uses the ambiguous active-session POST as a read operation.

History and trends support `start_time`, `end_time`, `card_number`, and `company_only`. Sessions use zero-based `page` and `limit`. Missing session date bounds default to the last 365 days through the current time, using `yyyy-MM-dd HH:mm:ss`, as used by the official app dashboard; supply both bounds to query older history. The management card displays this range and checks its order before sending a request. A failed request hides page totals rather than displaying zero energy. Trends optionally accept `trend_type`, as defined by the server protocol. The session date range was verified through live Home Assistant service calls: empty bounds returned HTTP 400, while explicit bounds and the integration defaults returned history successfully. Trend types still follow the server protocol. Logs use `log_from` as the starting serial number, with at most 50 records per request. Log records contain a timestamp, type, code, and detail code; the SDK's Chinese descriptions have not been copied.

## Schedules

```yaml
action: abb_chargersync.create_schedule
data:
  device_id: REPLACE_WITH_HA_DEVICE_ID
  start_time: "22:00"
  end_time: "06:00"
  enabled: true
```

`update_schedule` additionally requires `schedule_id`. `delete_schedule` requires only the device and `schedule_id`. Retrieve IDs using `get_data` with `resource: schedules`. Before an update or deletion, the ID is checked against this charger's current schedules. Times are sent to the cloud as `HH:MM`; the server uses device/account settings. No unverified UTC conversion is applied.

## Tariffs

```yaml
action: abb_chargersync.set_price
data:
  device_id: REPLACE_WITH_HA_DEVICE_ID
  settings:
    averagePrice: 0.30
```

Fields: `averagePrice`, `currencyType`, `midPeakSt`, `midPeakEt`, `midPeakPrice`, `offPeakSt`, `offPeakEt`, `offPeakPrice`, `onPeakSt`, `onPeakEt`, and `onPeakPrice`. Time windows use `HH:MM`; prices must be nonnegative. Retrieve current settings using `resource: price` and currency IDs using `resource: currencies`. Omitted fields are preserved. The integration does not calculate its own billing totals from untested tariff rules.

## Reports

`set_auto_export` accepts a `settings` object with required `enabled`. Optional fields are `format` (`csv`, `excel`, `pdf`), `cycle` (1, 3, or 6 months), `email`, `cardNumber`, and `isCompanyCarSession`. Other existing settings are preserved.

`export_sessions` requires `email`, `format`, `start_time`, and `end_time`. Optional filters are `card_number` and `company_only`. The official cloud sends the email.

`set_company_session` requires `session_id`, the `orderId` returned in cloud history, and `company`, a boolean. The integration checks up to 2,000 recent sessions from the selected charger before allowing the change.

## Timed current limits

`replace_load_limits` requires `ranges` and optionally accepts `enabled`. First retrieve the existing list using `resource: load_limits`.

Each range contains `weekdays` (protocol bitmask 1..127), `from` and `to` (seconds after midnight, 0..86400), and `limit` (amperes). The start must precede the end; split a window crossing midnight into two ranges. Maximum current is read from the charger before writing. At most 50 ranges are allowed. Exact weekday bit order and server interpretation of local time still require practical validation; a mask of 127 selects every day.

**This action replaces the complete list**, including any country-specific windows. Omitted ranges are removed. Existing random-delay settings are preserved. Use `ranges: []` with `enabled: false` to disable timed limits.

## Solar thresholds

Retrieve current values using `get_data` with `resource: solar_offsets`. `set_solar_offsets` accepts a `settings` object containing one or more of:

| Field | Meaning | Range |
|---|---|---|
| `solar_start_current` | Solar starting offset | 0..5 A |
| `solar_start_wait` | Solar starting wait time | 0..120 s |
| `solar_charging_current` | Solar charging offset | 0..5 A |
| `solar_charging_wait` | Solar charging wait time | 0..120 s |
| `eco_start_current` | Eco mix starting offset | 0..5 A |
| `eco_start_wait` | Eco mix starting wait time | 0..120 s |
| `eco_charging_current` | Eco mix charging offset | 0..5 A |
| `eco_charging_wait` | Eco mix charging wait time | 0..120 s |

The current configuration block is read again, and only supplied fields are changed. Limits follow SDK validation. These functions may be unavailable on older firmware.

## Charger name

`update_charger` takes `name`. Existing country/region, timezone, and firmware fields are preserved. Subsequent discovery uses the new cloud name; Home Assistant may retain device names you have explicitly set.
