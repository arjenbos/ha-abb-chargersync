# ChargerSync 3.5.0 — feature and API research

Investigated on October 25, 2026: `ChargerSync_3.5.0_APKPure.xapk`, package `com.abbemobility.chargersync`, version code `1757000011`. The version was confirmed in the Android manifest. The package contains the base APK and ARM64 and screen-density splits.

## Findings

The app provides a useful foundation for a Home Assistant integration. Three components matter: a REST cloud API for accounts and data, a cloud WebSocket for device commands, and a local Bluetooth interface. The WebSocket transports the binary device protocol also used by the Bluetooth library. An integration supporting only REST would probably miss functionality.

This is a static inventory of capabilities demonstrably present in this app package. No account was used, and no server or charger commands were executed. Code presence does not prove that every function is supported by a particular model, firmware version, or the current server. App features and additional SDK capabilities are described separately below.

This research inventory predates the integration's scope restrictions. Features listed here are not necessarily implemented; see the main README for the integration's supported scope.

## Features found in the app

| Area | Capabilities found | App evidence |
|---|---|---|
| Account | Registration, email verification, login, token refresh, profile reading/updating, password changes/recovery using a verification code, account deletion | `ApiManagerService`, account and login screens |
| Chargers | List/details, binding using device number and PIN, binding-status checks, removal/unbinding, renaming, country/region/timezone settings, PIN-reset requests | `addDevice`, `getDevices`, `updateDevice`, `resetPinCode`; setup and detail screens |
| Device identification | Bluetooth discovery, QR/product scanning, connection/reconnection, hardware/software information, online/network status, capability detection | Setup screens, `AbbBluetoothClient`, `Charger`, `QuerySysInfoResponse` |
| Charging control | Start, stop, read charging status, handle the active session, show a session summary | `startCharging`, `stopCharging`, `readChargingStatus`, charging screens; REST active-session declarations also exist |
| Measurements | L1/L2/L3 charging current and voltage, charged energy, session duration, rated current, phase configuration, session identifier, fault and unavailable codes | `ReadStatusResponse` fields; availability depends on response/model |
| Dashboard | Power, energy, cost, duration, configured/active charging mode, current limit and the channel/reason limiting current | `ChargeData`, dashboard, `ChannelInfoViewModel`; some values are derived |
| Current limiting | Read/set current and maximum output current, overall limit, timed current limits, read/add/update/delete plans | `writePowerControl`, `PowerControl`, `LoadBalanceFragment`, load-balancing plan methods |
| Charging schedules | Start/end times, enable/disable, read/create/update/delete schedules, country-specific windows, random delays, skip delayed charging | `ScheduleRequest`, REST schedules; `setSchedule`, `scheduledLimit`, `skipDelayedCharging` |
| Solar charging | Max speed, Eco mix, and Solar; solar-panel presence setting; default mode for future sessions and active-session mode; minimum current/threshold; Eco mix option to ignore the start/stop threshold | `ChargingMode`, `ChargingModeViewModel`, `switchSessionEnergyMode`, `configureDefaultSolarEnergyMode` |
| Solar data | Charging status and historical sessions with solar data, solar energy/share in summaries, compatibility and grid-meter identification | Solar response classes, session/statistics models, meter-selection screens |
| Free vending | Enable/disable charging without separate authorization | `FreeVendingFragment`, `enableOrDisableFreeVending` |
| RFID | Read, add/learn, name/update, hide through card data, delete, synchronize cloud/device card lists; filter sessions by card | RFID endpoints, card screens, `RFIDSyncManager`, `readRFIDCards`, `addRFIDCards`, `deleteRfidCards` |
| Cable | Read lock status, lock/unlock, release a stuck cable | `queryELockStatus`, `forceLock`, `forceUnlock`, `CableStuckFragment` |
| Network | Read/configure Wi-Fi, enable Ethernet/Wi-Fi/mobile connections, disable connections, mobile APN/username/password, network status, read/write TCP/IP settings | Network screens and wrapper methods; TCP/IP model supports DHCP/static IP, address, mask, gateway, DNS |
| History | Read local and solar sessions, synchronize to cloud, paginated cloud history, filter by period/card/company use, session details and stop reason | `SessionSyncService`, `SessionRepository`, `getSessions`, `Session` |
| Statistics | Trends/charts, energy, duration, cost, solar share, company-use flag, car/consumption settings and derived driving range | Statistics and car-capacity screens, `toggleCompanySession`, session model |
| Tariffs | Fixed/average tariff, off-/mid-/on-peak rates and windows, currency selection, tariff storage, estimated cost | `EnergyPlanRequest`, `getEnergyPlan`, `updateEnergyPlan`, cost dialog |
| Reports | Email session exports with format/period selection and card/company filters, read/configure automatic reports | `ExportSessionsRequest`, `AutoExportRequest`, export screens |
| Firmware | Installed version, available packages, upgrade/downgrade rules, start/cancel update transfer, progress/reboot status | Firmware endpoints, `startRemoteUpgrade`, `cancelRemoteUpgrade`, firmware screens |
| Diagnostics/support | Read/upload device logs, report connection results and device compatibility, display support and product notices | `queryDeviceLogInfo`, `queryDeviceLogsList`, log/support screens, event/notice endpoints |
| App settings | Notification preferences, register/unregister push tokens, profile settings, feedback/rating dialog | App settings, FCM endpoints, feedback screen |

According to the bundled app text, Solar uses excess solar energy only. Eco mix supplements solar energy with grid energy to meet the vehicle's minimum charging speed. Max speed selects the maximum available charging speed. These meanings come from app text, not practical testing.

Car/consumption settings and calculated driving range do not demonstrate access to the vehicle battery or an actual battery state of charge. Charts, costs, and percentages are not necessarily measured directly by the charger either.

## Additional SDK capabilities

The following functions occur in `CDBleClient`, `CMD`, and request/response classes. Their presence does not guarantee that the UI offers them or that a particular charge point accepts them:

- Request, transfer, and check OCPP server configuration.
- Read/write Modbus configuration; configure external/smart electricity meters, meter connectivity, and extended meter functions.
- Read/write I/O settings.
- Configure a fallback limit for loss of meter communication.
- Configure/read maximum phase imbalance.
- Add/read/delete VIN codes. This does not prove support for ISO 15118 Plug & Charge.
- Reset a charge point with parameters; exact reset types were not established.
- Synchronize time, configure sound, and enable power-saving mode.
- Query cumulative charging quantities and solar-related charging totals.
- Read IMEI and mobile-module information.
- Configure additional solar-mode offsets and waiting times.
- Read/write generic device configuration, supported connection modes, and storage information.
- Constants for electrical protection, socket, NFC, LAN, Wi-Fi, and grid configuration. A constant name is weaker evidence than an app-used function.

The technical appendix includes all 81 constant names covering 80 unique command numbers, all 122 extracted public SDK method signatures, app wrapper methods, and fields from 141 models. A7/F0 are shared commands with subfunctions; command count is not a count of user-facing features.

## API and authentication

REST base URL from `BuildConfig.API_HOST`: `https://abb-user.chargedot.com/`.

- Login: `POST api/oauth/token`, form fields `grant_type`, `client_id`, `client_secret`, `username`, `password`.
- Token refresh: the same path with refresh-token fields; implemented in `ProtectedRestclient`.
- The network layer sets `Authorization` using `token_type` and `access_token`.
- App version is sent through `X-APP-VERSION`.
- Device binding requires a device number and PIN. An account alone is insufficient to control arbitrary devices.
- For local connections, the app requests device-specific cipher data using `POST api/v2/devices/{id}/cipher`, stores/processes it through `SecureManager`, and initializes the SDK with it. The protocol includes encrypted authentication; the full local handshake was not reconstructed in this research pass.

There are 60 REST declarations representing 58 unique method/path combinations. The complete list, parameters, and response models are in the appendix and JSON inventory.

Notable duplication: `getActiveSessions` and `startSession` both use `POST api/v2/devices/{id}/sessions/active` but declare different response types. Token issuance and refresh also share a path. The active-session POST must not be treated as a proven side-effect-free status query.

WebSocket host from `BuildConfig.WEBSOCKET_HOST`: `wss://abb.api.chargedot.com:18971`.

`CDBleClient.init` normalizes the trailing slash and appends `ws/login?t=<sessionId>&v=1&e=<authen>`. Further inspection of `ui/base/BaseBluetoothFragment.java` confirms that these parameters come from `User.sessionId` and `User.authen`, not from the OAuth access token. Tokens and login identifiers must stay out of diagnostic logs.

`WebSocketClientImpl` processes `login`, `update_device_status`, and `remote_control`. Requests are JSON objects containing `method: remote_control`, `to: <device_number>`, and `data: <binary_payload_as_hex>`. Replies include `data.deviceNumber` and `data.raw`. The client sends a JSON `ping` every 30 seconds. This transports device commands; it is not a conventional JSON REST interface for every setting.

## Availability and local control

The app checks hardware/firmware, device capabilities, feature flags, cable status, active sessions, and connection type. For example, `DeviceSettingsSection` removes solar settings when the Solar feature flag is unavailable and removes cable controls when unsupported. Explicit states exist for Bluetooth required, unsupported, and active session.

Bluetooth suggests local control is possible, but fully cloud-independent commissioning has not been demonstrated: the app retrieves authentication material from the cloud. Retention and offline usability require further investigation.

Wi-Fi/Ethernet configuration does not prove the existence of a local HTTP API. The SDK includes Modbus and OCPP configuration, but this does not establish that Home Assistant can communicate directly with a charger over the LAN.

## Implications for Home Assistant

Based on this APK, charging status, availability, session energy, duration, per-phase current/voltage, and fault status are sensor candidates. Power, cost, and solar share require source/unit verification. Start/stop, current limits, charging modes, free vending, and cable control are control-entity candidates; schedules and RFID could use additional actions.

Exact entities, value ranges, polling intervals, and concurrent operation with the official app require account/device testing. This inventory records discovered possibilities rather than selecting integration features. The implemented integration's scope is documented separately in the main README.

## Research limitations and provenance

The investigation used local extraction and JADX. MCP code-graph tools were unavailable in the session, so file/text inspection was used instead. Supplied files were treated as research data.

JADX reported 326 errors across the APK, including incompletely decompiled methods and Kotlin enums. The main API interface, wrapper, SDK, and models were available, but this prevents guaranteeing discovery of every feature and code path. Native ARM64 libraries were not separately reverse-engineered. No dynamic network trace or live server validation was performed.

Key evidence files, relative to the decompiled `sources` directory:

- `com/abbemobility/chargersync/networking/ApiManagerService.java`: all REST declarations.
- `com/abbemobility/chargersync/managers/AbbBluetoothClient.java`: app controls and connection initialization.
- `com/chargedot/bluetooth/library/CDBleClient.java`: SDK functions and authentication/transport.
- `com/chargedot/bluetooth/library/WebSocketClientImpl.java`: WebSocket envelopes and reply handling.
- `com/chargedot/bluetooth/library/CMD.java`: command numbers.
- `com/abbemobility/chargersync/ui/main/devicesettings/chargingMode/ChargingModeViewModel.java`: solar settings and additional subcommands.
- `com/abbemobility/chargersync/constants/DeviceSettingsSection.java`: features and visibility.
- `com/chargedot/bluetooth/library/response/ReadStatusResponse.java`: measurement and status fields.
- `resources/res/values/strings.xml`: feature labels and explanations.

See [technical-appendix.md](technical-appendix.md) for the readable inventory and [technical-inventory.json](technical-inventory.json) for implementation reuse. Appendix line numbers refer to local JADX output, not original ABB source code.
