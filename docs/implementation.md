# Implementation and limitations

## Architecture

- `api.py`: aiohttp REST client, password grant during configuration, serialized token refresh, and a token persistence callback. No account, RFID, or binding management.
- `protocol.py`: framing, XOR checksum, bounded incremental decoder, cloud identity authentication, and status/configuration parsers.
- `websocket.py`: one persistent WSS connection per device with a background reader, a serialized command stream, JSON pings, reconnect backoff, and cleanup when the stream becomes ambiguous. No Bluetooth transport.
- `controller.py`: typed device operations, current-limit validation, and read-modify-write operations for solar and timed-limit settings.
- `coordinator.py`: cloud inventory, per-device remote connections, refreshing, availability, and discovery.
- Platform modules: Home Assistant entities created when a capability is successfully read.
- `services.py`: actions with input schemas and device, schedule, and session ownership checks.
- `diagnostics.py`: limited diagnostics without account or device identifiers.

The Home Assistant layer follows the configuration flow, runtime data, and DataUpdateCoordinator patterns in the [official developer documentation](https://developers.home-assistant.io/docs/integration_fetching_data/).

## Protocol evidence

The APK's cloud connection path explicitly disables encrypted Bluetooth mode before opening the WebSocket. The same frame format is transported over WSS; supporting that format does not require Bluetooth functionality.

Unencrypted protocol frames contain eight header bytes, eight device-token bytes, and the body. Body length is little-endian, and XOR across the complete frame is zero. The authentication body contains the device number and SDK user ID, which the app SDK initializes to 0, encrypted using DES/ECB/PKCS5Padding with the public SDK key and a padded block. The implementation uses TripleDES with the same key repeated three times to produce the equivalent legacy DES transformation. WSS provides transport security.

After WSS login, device authentication and time synchronization follow the Android SDK sequence. The returned device token remains in memory only. Bluetooth cipher material is not required.

The URL uses `/ws/login`. `CDBleClient.init` normalizes the trailing slash before appending this path. `BaseBluetoothFragment` supplies `User.authen` as the `e` parameter and `User.sessionId` as the `t` parameter. These are distinct from the REST OAuth access token. The client retrieves this pair from the authenticated user-profile endpoint and keeps it only in memory; rejected remote sessions invalidate that cache. Tests explicitly assert that the WebSocket uses the profile session rather than the OAuth token.

`getActiveSessions` and `startSession` share the same POST path in the APK. The integration never uses this path to read status. Start and stop operations use explicit device commands.

Measurement scaling follows the SDK parsers: legacy session energy /100 kWh, solar session energy /1000 kWh, and current/voltage /100. Cable status is 1=locked and 2=unlocked. Solar/Eco mix/Max speed use protocol values 3/2/1. This decoding has been tested with synthetic frames.

## Connection lifetime

Every connection repeats the sequence from `CDBleClient` and `WebSocketClientImpl`: cloud
login (`/ws/login?t=<sessionId>&v=1&e=<authen>`), identity authentication (command 254)
and time synchronization (command 176). The SDK treats a failed time synchronization as
a failed connection, and resets the device token to zeros on every disconnect, so neither
step can be skipped or reused. Chargers can audibly signal this login. The integration
therefore keeps the connection open:

- The OAuth access token is not part of the WebSocket session. Refreshing it does not reconnect.
- A complete reply with a non-zero frame result code, frame codes 20/21, or a non-zero,
  non-401 cloud `remote_control` code rejects only that command. Timeouts, transport errors,
  invalid frames or envelopes, closes, cloud code 401, and `update_device_status` 1/3/-1
  end the connection. The last three also end it in the app.
- A background task reads all messages, as the app's listener does. The app sends a JSON
  `ping` every 30 seconds while the socket is open and has no idle timeout. The integration
  does the same.
- After one immediate retry, which the app also performs, reconnects back off from 30 seconds
  to 10 minutes. A connection that lasted 5 minutes resets the backoff. User actions bypass it.
- The REST `online` flag only prevents opening a new connection; it does not close a live one.
- One remote session per account: when another client signs in, the cloud resets this
  connection with TCP close code 1006. A login with the cached `sessionId` then returns
  `login` code 1 until the profile is read again. The profile's `sessionId` has then changed. The
  integration counts that change by digest only and waits 10 minutes before reclaiming, doubling
  up to 60 minutes. A Docker test on November 16, 2026 reproduced the cycle against a production
  install on the same account: connections lasted 0–70 seconds.

The **Remote logins** sensor and diagnostics report the connect count, open state, last
disconnect reason, connection age and reconnect delay, without identifiers or payloads.

## Additional app and SDK reads

- **Lifetime energy:** `READ_TOTAL_CHARGE_CMD` (184) has no request body. `QueryChargeQuantityResponse` reads a little-endian uint32 and divides it by 100 to give kWh. Command 174 (`QUERY_ACCUMULATED_CHARGING_POWER_WITH_SOLAR_ENERGY_INFO`) takes one request byte and returns unscaled total and solar totals. The integration sends the same port byte as the verified solar status read. On November 16, 2026, a live read returned 4959409 from command 174 while command 184 reported 4959.4 kWh, so 174 is in Wh. The integration uses 184 for lifetime energy and 174's second field for lifetime solar energy. The app calls neither command.
- **Grid meter status:** `QUERY_METER_CONNECT_STATUS` (229) has no request body. It returns a status byte and a little-endian uint32 master/Modbus status. The app does not call it or define meanings for these values.
- **Cable release:** the app's stuck-cable screen sends the same commands as the lock entity, `FORCE_UNLOCK` (209) and `FORCE_LOCK` (231). `ChargerCapabilitiesUtils` limits release to socket outlets on FX devices or firmware 1.6.8 or later. Locking also needs firmware 1.8.2 or later and a remote feature flag that cannot be read here. The integration applies these firmware and outlet checks when the cloud reports the fields.
- **RFID cards:** `GET api/v2/rfid-cards?showHidden=false` lists account cards with `name`, `serialNumber`, `deviceId`, and `status`. The integration reads them with the five-minute inventory and never writes them.
- **Firmware notice:** `GET api/v2/notices?deviceNumber=<number>&type=firmware_upgrade` returns `title` and `content`, as on the app's charging screen.
- **Device logs:** commands 188/189 remain available through `get_data` (`log_info`, `logs`).

## Sound volume

`CDBleClient.setVoice` sends `SET_VOICE_CMD` (178) with the body `[volume, 1]`, where volume
is 0–100. The reply's first byte is the result code. `QuerySysInfoResponse` reads the current
volume from body byte 61 of the `READ_SYS_INFO_CMD` (177) reply. The ABB app never calls
`setVoice`, so the volume entity is experimental. Its effect on the login beep and on other
charger sounds has not been verified.

## Limitations

- Live read-only testing has confirmed cloud authentication, remote status, current-limit reading, and several configuration reads on one charger with firmware 1.8.37. Write effects and broader hardware compatibility remain experimental.
- Not every SDK capability is an app feature. Installer configuration is not exposed through arbitrary cloud actions.
- The official app requires Bluetooth for firmware installation and network settings; both are excluded.
- Different connectors/ports are not modeled as separate charge points. The investigated app reads status for port 0; current control uses the port returned by the device. Multiport chargers require additional validation.
- The server may limit polling. At most three devices are read concurrently, with commands serialized for each device. Default polling intervals are 30 seconds for remote state and 300 seconds for REST inventory.
- A write timeout raises an error with a potentially unknown outcome. The integration does not automatically repeat the mutation.
- The timed-limit action replaces all ranges. Weekday bit order and server date/trend formats have not been guessed.
- User passwords are not stored; refresh tokens are included in Home Assistant storage and backups. Standard Home Assistant access protection remains relevant.

The original APK analysis is under `docs/research`. That inventory covers more capabilities than the explicitly limited scope of this integration.


## Session history date range

The local ChargerSync 3.5.0 APK provides two relevant sources:
`repositories/SessionRepository.java` starts history pagination at page zero, and
`ui/main/dashboard/DashboardViewModel.java` supplies a date range from one year
ago to the current time. `constants/TimeFormats.java` defines `DATE_TIME_API` as
`yyyy-MM-dd HH:mm:ss`. These paths are relative to
`com/abbemobility/chargersync/` in the decompiled sources.

The REST client supplies missing session date bounds using the last 365 days
through the current time, including background reads and session ownership
checks. Explicit bounds remain unchanged so older history can be requested.
The management card shows its range, rejects reversed dates locally, and hides
page totals and pagination on failed history reads. Successful empty responses
still show an empty page.

Live Home Assistant service checks on October 25, 2026 confirmed that empty
bounds returned HTTP 400, while explicit bounds and the integration defaults
each returned seven sessions. This verifies the date-range behavior for the
tested account; it does not establish all possible cloud validation rules.


## Reading load-balancing plans

Command 164 (`SCHEDULED_LIMIT`) reads settings with the single-byte body `02`.
The APK's `AbbBluetoothClient.readLoadBalancingPlans` uses the default mode 2
from `scheduledLimit$default`; `RequestBodyFactory.scheduledLimitRequestBody`
emits only that mode byte for a read. Mode 0 is not the query operation.
Both direct reads and reads before modifying timed limits or skipping a delay
use mode 2. The reply parser still rejects incomplete settings so writes cannot
silently replace unknown configuration with defaults.

Two live reads on October 25, 2026 succeeded after correcting the mode, reporting
timed limits enabled with zero configured ranges. No charger settings were
changed during these checks. Service ownership uses the Home Assistant device's
singular `config_entry_id`, avoiding the deprecated `config_entries` property.


## Remote login diagnostics and recovery

Remote failures record a fixed reason and numeric result code, excluding cloud
payloads and credentials. A failed WebSocket login handshake invalidates cached
profile credentials, including when the connection closes or times out before
a login reply. The next poll fetches the profile again; commands are not replayed.

Live polling on October 25, 2026 captured `cloud_login`, `login_rejected`, result
code 1. This identifies a server login rejection but does not establish why the
server rejects it. The active-mode configuration query separately returns result
code 1; its query type 9 matches the APK. Neither code is treated as proof that
the feature is unsupported, and neither warning is suppressed.
