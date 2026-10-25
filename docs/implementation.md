# Implementation and limitations

## Architecture

- `api.py`: aiohttp REST client, password grant during configuration, serialized token refresh, and a token persistence callback. No account, RFID, or binding management.
- `protocol.py`: framing, XOR checksum, bounded incremental decoder, cloud identity authentication, and status/configuration parsers.
- `websocket.py`: WSS envelopes, one serialized command stream per device, JSON pings, and connection cleanup on errors. No Bluetooth transport.
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
