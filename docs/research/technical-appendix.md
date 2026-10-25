# ChargerSync 3.5.0 — technical appendix

Static extraction; no live confirmation. Source paths are relative to the decompiled sources. Line numbers refer to JADX output. Reference counts measure textual calls, not proven reachability.

## All REST declarations

| Method | Path | App function | References | Source line |
|---|---|---|---:|---:|
| POST | `api/v2/devices/bind` | `addDevice` | 1 | 74 |
| POST | `api/v2/users/me/password` | `changePassword` | 2 | 78 |
| POST | `/api/v2/devices-compatibility/{deviceNumber}` | `createOrUpdateDeviceCompatibility` | 3 | 81 |
| POST | `api/v2/rfid-cards` | `createRfidCard` | 3 | 84 |
| POST | `api/v2/devices/{id}/schedules` | `createSchedule` | 5 | 87 |
| DELETE | `api/v2/devices/{id}` | `deleteDevice` | 1 | 90 |
| DELETE | `api/v2/rfid-cards/{id}` | `deleteRfidCard` | 3 | 93 |
| DELETE | `api/v2/schedules/{id}` | `deleteSchedule` | 5 | 96 |
| DELETE | `api/v2/users/me` | `deleteUser` | 4 | 99 |
| POST | `api/v2/devices/{id}/sessions/export` | `exportDeviceSessions` | 4 | 102 |
| GET | `/api/v2/device/prefix` | `fetchDevicePrefixList` | 2 | 105 |
| GET | `/api/v2/notices` | `fetchNotice` | 2 | 108 |
| GET | `api/v2/regions/{code}` | `fetchRegion` | 6 | 111 |
| GET | `api/v2/countries/{code}/regions` | `fetchRegions` | 3 | 114 |
| POST | `api/v2/devices/{id}/sessions/active` | `getActiveSessions` | 3 | 117 |
| GET | `api/v2/users/me/app-settings` | `getAppSettings` | 7 | 120 |
| GET | `api/v2/devices/{id}/sessions/auto-export` | `getAutoExport` | 11 | 123 |
| POST | `api/v2/devices/{id}/cipher` | `getCipherForCharger` | 1 | 126 |
| GET | `api/v2/countries` | `getCountries` | 8 | 129 |
| GET | `api/v2/countries/{country}` | `getCountry` | 10 | 132 |
| GET | `api/v2/currencies` | `getCurrencies` | 13 | 135 |
| GET | `api/v2/devices/{id}` | `getDevice` | 3 | 138 |
| GET | `api/v2/devices/bound` | `getDeviceBoundStatus` | 1 | 141 |
| GET | `api/v2/devices/{id}/trends` | `getDeviceTrends` | 7 | 144 |
| GET | `api/v2/devices` | `getDevices` | 11 | 147 |
| GET | `api/v2/devices/upgrade-rules/downgrade` | `getDowngradeRules` | 0 | 150 |
| GET | `api/v2/devices/{id}/price` | `getEnergyPlan` | 9 | 153 |
| GET | `api/v2/devices/{id}/latest-upgrade-packages` | `getFirmware` | 0 | 156 |
| GET | `/api/v2/grid-meters` | `getGridMeters` | 1 | 159 |
| GET | `/api/v2/public/notices` | `getNotice` | 3 | 162 |
| GET | `api/v2/rfid-cards/{id}` | `getRfidCard` | 10 | 165 |
| GET | `api/v2/rfid-cards` | `getRfidCards` | 21 | 168 |
| GET | `api/v2/devices/{id}/schedules` | `getSchedules` | 13 | 171 |
| GET | `api/v2/devices/{id}/sessions` | `getSessions` | 4 | 174 |
| GET | `api/v2/devices/upgrade-rules/upgrade` | `getUpgradeRules` | 0 | 177 |
| GET | `api/v2/users/me` | `getUser` | 26 | 180 |
| POST | `api/oauth/token` | `loginWithPassword` | 1 | 184 |
| POST | `api/oauth/token` | `refreshToken` | 1 | 188 |
| POST | `api/v2/users/register` | `register` | 2 | 192 |
| POST | `api/v2/reset-password` | `requestPasswordReset` | 4 | 195 |
| POST | `api/v2/forgot-password` | `requestPasswordReset` | 4 | 199 |
| POST | `api/v2/devices/{id}/reset-pincode` | `resetPinCode` | 5 | 203 |
| POST | `api/v2/devices/{id}/sessions/active` | `startSession` | 1 | 206 |
| DELETE | `api/v2/active-sessions/{id}` | `stopSession` | 1 | 209 |
| POST | `/api/v2/registry/notifications/token` | `syncFCMToken` | 2 | 212 |
| POST | `api/v2/sessions/{id}` | `toggleCompanySession` | 4 | 215 |
| POST | `/api/v2/unregistry/notifications/token` | `unregisterFCMToken` | 1 | 218 |
| POST | `api/v2/devices/{id}/sessions/auto-export` | `updateAutoExport` | 7 | 221 |
| POST | `api/v2/devices/{id}` | `updateDevice` | 1 | 224 |
| POST | `api/v2/devices/{id}/price` | `updateEnergyPlan` | 4 | 227 |
| POST | `api/v2/users/me/app-settings` | `updateNotifications` | 4 | 230 |
| POST | `api/v2/rfid-cards/{id}` | `updateRfidCard` | 5 | 233 |
| PUT | `api/v2/rfid-cards` | `updateRfidCards` | 5 | 236 |
| POST | `api/v2/schedules/{id}` | `updateSchedule` | 4 | 239 |
| POST | `api/v2/users/me` | `updateUser` | 3 | 242 |
| POST | `api/v2/devices/{id}/sessions` | `uploadChargeSessions` | 1 | 245 |
| POST | `/api/v2/bluetooth/device/logs/upload/{deviceNumber}` | `uploadChargerLogs` | 2 | 248 |
| POST | `api/v2/events/connect` | `uploadConnectResult` | 2 | 251 |
| POST | `api/v2/users/verify` | `verifyAccount` | 1 | 255 |
| POST | `api/v2/verify-reset-password-code` | `verifyPasswordResetCode` | 3 | 259 |

Note: `getActiveSessions` and `startSession` use the same POST path with different response types. Read behavior and side effects must be established before live use.

## Request and response fields

These are Java fields. Derived UI models do not guarantee an identical JSON wire format.

### `com/abbemobility/chargersync/data/entities/ActiveSession.java`

`float batteryId`, `int cost`, `String deliveredWh`, `int deviceId`, `String elapsedDuration`, `String id`, `int maxCurrentAmps`, `float startTime`

### `com/abbemobility/chargersync/data/entities/Alert.java`

`String body`, `String title`

### `com/abbemobility/chargersync/data/entities/AppSettings.java`

`App app`, `String id`, `List<Notifications> notifications`, `int userId`

### `com/abbemobility/chargersync/data/entities/AutoExport.java`

`String cardNumber`, `Integer cycle`, `String email`, `boolean enabled`, `String format`, `Boolean isCompanyCarSession`, `int userId`

### `com/abbemobility/chargersync/data/entities/AutoExportRequest.java`

`String cardNumber`, `Integer cycle`, `String email`, `boolean enabled`, `String format`, `Boolean isCompanyCarSession`

### `com/abbemobility/chargersync/data/entities/ChargeData.java`

`ChargingMode activeChargingMode`, `String channelInfo`, `ChargingMode chargingMode`, `ChargingModeParam chargingModeParam`, `String cost`, `String duration`, `Double energy`, `boolean hasSolarCompatibleModbus`, `boolean hasSolarPanels`, `Boolean isFreeVendingActive`, `Integer maximumCurrentOutput`, `Double power`, `int solarPercentage`, `Integer userInputCurrent`

### `com/abbemobility/chargersync/data/entities/Charger.java`

`String address`, `String aliasNumber`, `ArrayList<String> certified`, `long chargeType`, `Cipher cipher`, `DeviceCompatibility compatibility`, `String countryCode`, `boolean countryRequired`, `String deviceNumber`, `long elecPower`, `String hardwareModel`, `String hardwareVersion`, `int id`, `boolean isLastConnected`, `boolean isPublic`, `String latitude`, `String longitude`, `String model`, `ArrayList<String> netModule`, `long netType`, `int online`, `String outlet`, `String partNumber`, `String pinCode`, `ArrayList<Port> ports`, `long powerType`, `Integer productType`, `long ratedCurrent`, `String regionCode`, `String softVersion`, `long stationId`, `long status`, `SupportContainer support`

### `com/abbemobility/chargersync/data/entities/ChargingModeParam.java`

`float avoidInjectActiveOffset`, `byte avoidInjectActiveWaitingTimeSeconds`, `float avoidInjectDefaultOffset`, `byte avoidInjectDefaultWaitingTimeSeconds`, `float solarActiveOffset`, `byte solarActiveWaitingTimeSeconds`, `float solarDefaultOffset`, `byte solarDefaultWaitingTimeSeconds`

### `com/abbemobility/chargersync/data/entities/Cipher.java`

`String info`, `String secretKey`

### `com/abbemobility/chargersync/data/entities/Country.java`

`Alert alert`, `String code`, `String countryCode`, `boolean hasRegions`, `double latitude`, `double longitude`, `String name`, `CountrySpecificParameters parameters`

### `com/abbemobility/chargersync/data/entities/CountrySpecificParameters.java`

`CountrySpecificSchedule schedule`

### `com/abbemobility/chargersync/data/entities/CountrySpecificSchedule.java`

`List<CountrySpecificSchedulePlan> plan`, `int randomizedDelay`

### `com/abbemobility/chargersync/data/entities/CountrySpecificSchedulePlan.java`

`String endTime`, `boolean limitAmperage`, `int maximumCurrent`, `String name`, `int repeat`, `String startTime`

### `com/abbemobility/chargersync/data/entities/Currency.java`

`Integer currencyRatio`, `Integer currencyType`, `int id`, `String name`, `String symbol`, `String tag`

### `com/abbemobility/chargersync/data/entities/CustomDate.java`

`String endTime`, `String startTime`

### `com/abbemobility/chargersync/data/entities/DaySet.java`

`byte days`

### `com/abbemobility/chargersync/data/entities/DeviceCompatibility.java`

`Boolean solar`

### `com/abbemobility/chargersync/data/entities/DeviceTrends.java`

`int currencyType`, `int id`, `ArrayList<Trend> trends`

### `com/abbemobility/chargersync/data/entities/DowngradeUpgradePackage.java`

`Boolean autoInstall`, `String checksum`, `boolean doFirmwareNotice`, `String featureDetails`, `boolean isBleEncryptionPack`, `Boolean isMandatory`, `String name`, `String url`

### `com/abbemobility/chargersync/data/entities/DowngradeUpgradeRule.java`

`Integer deviceId`, `int id`, `DowngradeUpgradePackage packageInfo`, `Boolean ruleIsForUpdate`, `String version`

### `com/abbemobility/chargersync/data/entities/EnergyPlan.java`

`String averagePrice`, `int currencyType`, `int deviceId`, `int id`, `String midPeakEt`, `String midPeakPrice`, `String midPeakSt`, `String offPeakEt`, `String offPeakPrice`, `String offPeakSt`, `String onPeakEt`, `String onPeakPrice`, `String onPeakSt`, `int open`, `String priceDetail`

### `com/abbemobility/chargersync/data/entities/FCM.java`

`String currentToken`, `int id`, `String lastToken`

### `com/abbemobility/chargersync/data/entities/Firmware.java`

`int applyPower`, `String applyVersion`, `String checksum`, `String createdAt`, `int deviceId`, `boolean doFirmwareNotice`, `String downloadPath`, `ArrayList<String> featureDetails`, `int id`, `int isBleEncryptionPack`, `int len`, `String model`, `String name`, `String softVersion`, `int upgradeType`

### `com/abbemobility/chargersync/data/entities/GraphModel.java`

`String name`, `float value`

### `com/abbemobility/chargersync/data/entities/GridMeter.java`

`String id`, `String manufacturer`, `String model`, `String series`, `boolean solar`, `String subModel`, `boolean tcp`

### `com/abbemobility/chargersync/data/entities/LocalSession.java`

`int chargeElectricity`, `int deviceId`, `int duration`, `int endTime`, `int nettingMode`, `int portId`, `int seq`, `Integer solarEnergy`, `int startTime`, `int startingMode`, `int stopReason`, `Integer timeZone`, `String userIdContent`, `int userIdType`, `int userType`

### `com/abbemobility/chargersync/data/entities/NoticeResponse.java`

`String content`, `String title`

### `com/abbemobility/chargersync/data/entities/Plan.java`

`List<? extends DayOfWeek> errorWeekdays`, `String from`, `byte limit`, `byte repeatForDays`, `String to`, `byte weekdays`

### `com/abbemobility/chargersync/data/entities/Port.java`

`long adjustCurrent`, `String detail`, `long deviceId`, `long deviceLevel`, `String deviceNumber`, `long id`, `long occupyUserId`, `String portNumber`, `long portType`, `long portTypeDetail`, `long reduceRatio`, `long stationId`, `long status`

### `com/abbemobility/chargersync/data/entities/Region.java`

`Alert alert`, `String code`, `Country country`, `String countryCode`, `double latitude`, `double longitude`, `String name`, `CountrySpecificParameters parameters`

### `com/abbemobility/chargersync/data/entities/RegionWithCountry.java`

`Country country`, `Region region`

### `com/abbemobility/chargersync/data/entities/RemoteKeys.java`

`Integer nextKey`, `Integer prevKey`, `String repoId`

### `com/abbemobility/chargersync/data/entities/RfidCard.java`

`String createdAt`, `Integer deviceId`, `String email`, `String id`, `boolean isSelected`, `String name`, `String serialNumber`, `Integer status`, `String updatedAt`, `Integer userId`

### `com/abbemobility/chargersync/data/entities/RuleResponse.java`

`DowngradeUpgradeRule rule`

### `com/abbemobility/chargersync/data/entities/Schedule.java`

`Integer deviceId`, `String endTime`, `int id`, `Integer open`, `String startTime`, `Integer userId`

### `com/abbemobility/chargersync/data/entities/SecureCipher.java`

`byte[] info`, `byte[] infoIv`, `byte[] secretKey`, `byte[] secretKeyIv`

### `com/abbemobility/chargersync/data/entities/Session.java`

`int abnormal`, `String chargeFinishReason`, `float cost`, `int currencyType`, `int duration`, `float energy`, `int isCompanyCarSession`, `String orderId`, `long range`, `Integer solarEnergy`, `String startTime`, `int startType`, `String stopTime`, `String userCodeDetail`, `int userCodeType`, `int userId`, `int userType`

### `com/abbemobility/chargersync/data/entities/SessionRemoteKeys.java`

`String itemId`, `Integer nextKey`, `Integer prevKey`

### `com/abbemobility/chargersync/data/entities/Trend.java`

`float cost`, `String date`, `int duration`, `float energy`, `int trans`

### `com/abbemobility/chargersync/data/entities/User.java`

`Integer accept`, `String authen`, `String createdAt`, `Currency currency`, `String face`, `Integer forbidStatus`, `int id`, `String name`, `String sessionId`, `Integer timeZone`

### `com/abbemobility/chargersync/networking/requests/ConnectRequest.java`

`int connectedMode`, `String deviceNumber`, `String firmwareVersion`, `int result`, `int supportedMode`, `String timestamp`

### `com/abbemobility/chargersync/networking/requests/CreateRfidRequest.java`

`int deviceId`, `String email`, `String name`, `String serialNumber`

### `com/abbemobility/chargersync/networking/requests/EnergyPlanRequest.java`

`String averagePrice`, `int currencyType`, `String midPeakEt`, `String midPeakPrice`, `String midPeakSt`, `String offPeakEt`, `String offPeakPrice`, `String offPeakSt`, `String onPeakEt`, `String onPeakPrice`, `String onPeakSt`, `int open`

### `com/abbemobility/chargersync/networking/requests/ExportSessionsRequest.java`

`String cardNumber`, `String email`, `String endTime`, `String format`, `Boolean isCompanyCarSession`, `String startTime`

### `com/abbemobility/chargersync/networking/requests/NotificationsRequestValues.java`

`boolean endOfChargingSession`, `boolean exportMonthlyReminder`, `boolean newSoftwareUpdateAvailable`, `boolean startOfChargingSessionBySomeoneElse`

### `com/abbemobility/chargersync/networking/requests/NotificationsValues.java`

`String key`

### `com/abbemobility/chargersync/networking/requests/ResetPasswordRequest.java`

`String code`, `String confirmPassword`, `String email`, `String password`

### `com/abbemobility/chargersync/networking/requests/ScheduleRequest.java`

`String endTime`, `Integer open`, `String startTime`

### `com/abbemobility/chargersync/networking/requests/UnregisterFCMTokenRequest.java`

`String token`, `int userId`

### `com/abbemobility/chargersync/networking/requests/UpdateChargerRequest.java`

`String aliasNumber`, `String countryCode`, `String regionCode`, `String softVersion`, `String timeZone`

### `com/abbemobility/chargersync/networking/requests/UpdateCompanyCarRequest.java`

`boolean isCompanyCarSession`

### `com/abbemobility/chargersync/networking/requests/UpdateFCMRequest.java`

`String oldToken`, `String token`, `int userId`

### `com/abbemobility/chargersync/networking/requests/UpdateNotificationsRequest.java`

`NotificationsRequestValues notifications`

### `com/abbemobility/chargersync/networking/requests/UpdateRfidCard.java`

`String email`, `String name`, `String serialNumber`

### `com/abbemobility/chargersync/networking/requests/UpdateRfidListRequest.java`

`List<UpdateRfidCard> cards`, `int deviceId`

### `com/abbemobility/chargersync/networking/requests/UpdateRfidRequest.java`

`String email`, `String name`

### `com/abbemobility/chargersync/networking/requests/UpdateUserRequest.java`

`String email`, `String name`

### `com/abbemobility/chargersync/networking/requests/UploadChargerLogsReq.java`

`List<Log> logs`

### `com/abbemobility/chargersync/networking/requests/UploadDeviceSessions.java`

`List<LocalSession> sessions`

### `com/abbemobility/chargersync/networking/responses/CipherResponse.java`

`Cipher cipher`, `String deviceNumber`, `int userId`

### `com/abbemobility/chargersync/networking/responses/CountryCompactResponse.java`

`boolean hasRegions`, `List<RegionCompactResponse> regions`

### `com/abbemobility/chargersync/networking/responses/CountryDetailResponse.java`

`boolean hasRegions`, `List<RegionCompactResponse> regions`

### `com/abbemobility/chargersync/networking/responses/LocationCompactResponse.java`

`Alert alert`, `String countryCode`, `double latitude`, `double longitude`

### `com/abbemobility/chargersync/networking/responses/LocationDetailResponse.java`

`CountrySpecificParameters parameters`

### `com/chargedot/bluetooth/library/model/ActiveSolarEnergyModeConfiguration.java`

`ControlMode controlMode`, `int userInputCurrent`

### `com/chargedot/bluetooth/library/model/BleGattCharacter.java`

`List<BleGattDescriptor> descriptors`, `int permissions`, `int property`, `ParcelUuid uuid`

### `com/chargedot/bluetooth/library/model/BleGattDescriptor.java`

`int mPermissions`, `ParcelUuid mUuid`, `byte[] mValue`

### `com/chargedot/bluetooth/library/model/BleGattProfile.java`

`List<BleGattService> services`

### `com/chargedot/bluetooth/library/model/BleGattService.java`

`List<BleGattCharacter> characters`, `ParcelUuid uuid`

### `com/chargedot/bluetooth/library/model/BleModbus.java`

`int meterSlaveAddress`, `int modbusMode`, `int modbusProtocolType`, `int modbusType`, `int rtuCommunicationStopBit`, `int rtuCommunicationVerifyBit`, `int rtuIV`, `String tcpGateway`, `String tcpIpAddress`, `String tcpMaskAddress`, `int tcpPort`

### `com/chargedot/bluetooth/library/model/ChargerTcpIpConfiguration.java`

`String gatewayAddress`, `String ipAddress`, `String maskAddress`, `NetworkMode mode`, `String primaryDnsAddress`, `NetworkType type`

### `com/chargedot/bluetooth/library/model/DefaultSolarEnergyModeConfiguration.java`

`ControlMode controlMode`, `ControlVia controlVia`, `int delayTime`, `boolean isEnable`, `int userInputCurrent`

### `com/chargedot/bluetooth/library/model/PowerControl.java`

`int maxOutputCurrent`, `int outputCurrent`, `int port`

### `com/chargedot/bluetooth/library/model/SmartMeter.java`

`int controlLimit`, `int controlLower`, `int elecpricPowerCapacity`, `int enableLocalLoadManagement`, `int enableMasterMode`, `int enableSmartMeter`, `byte[] extraBytes`, `int meterAddress`, `String modbus`, `int modbusProtocolType`, `int modbusRTU`, `String modbusTcpGetewayAddress`, `String modbusTcpIpAddress`, `int modbusTcpPort`, `String modbusTcpSubnetMaskAddress`, `int slaveCount`

### `com/chargedot/bluetooth/library/model/SolarEnergyModeOffsetConfiguration.java`

`float chargingOffsetForAvoidInjectionMode`, `float chargingOffsetForSolarOnlyMode`, `int chargingWaitTimeForAvoidInjectionMode`, `int chargingWaitTimeForSolarOnlyMode`, `float prechargingOffsetForAvoidInjectionMode`, `float prechargingOffsetForSolarOnlyMode`, `int prechargingWaitTimeForAvoidInjectionMode`, `int prechargingWaitTimeForSolarOnlyMode`

### `com/chargedot/bluetooth/library/response/ActiveAddCardResponse.java`

`String cardNumber`

### `com/chargedot/bluetooth/library/response/CDBleResponse.java`

`int bodyLength`, `int cmdType`, `String errorMsg`

### `com/chargedot/bluetooth/library/response/ChangeNetModeResponse.java`

`String detailDesc`

### `com/chargedot/bluetooth/library/response/CheckNetworkStatusResponse.java`

`int networkingMode`, `int resultTheDetail`, `String resultTheDetailDesc`

### `com/chargedot/bluetooth/library/response/ConfigurationResponse.java`

`int action`, `String content`

### `com/chargedot/bluetooth/library/response/ConfigurationWifiNetworkResponse.java`

`String detailDesc`

### `com/chargedot/bluetooth/library/response/ConfigureA7Response.java`

`byte result`, `short type`

### `com/chargedot/bluetooth/library/response/ConfigureActiveSolarEnergyModeResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/ConfigureChargerTcpIpConfigurationResponse.java`

`Integer result`, `ChargerTcpIpConfiguration.NetworkType type`

### `com/chargedot/bluetooth/library/response/ConfigureDefaultSolarEnergyModeResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/ConfigureElectricMeterModbusResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/ConfigureElectricMeterResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/ConfigureFallbackResponse.java`

`int reason`, `int result`

### `com/chargedot/bluetooth/library/response/ConfigureIOSettingsResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/ConfigureMaximumPhaseImbalanceResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/ConfigureSolarEnergyModeOffsetResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/ConfigureSupportsConnectionResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/DeviceConfigResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/DeviceReportResponse.java`

`byte[] content`, `int function`, `int length`

### `com/chargedot/bluetooth/library/response/EncryptedIdentityAuthResponse.java`

`byte index`, `byte result`

### `com/chargedot/bluetooth/library/response/ForceLockResponse.java`

`int detail`, `int rawDetail`, `int result`

### `com/chargedot/bluetooth/library/response/ForceUnlockResponse.java`

`String detailDesc`

### `com/chargedot/bluetooth/library/response/GetStorageInfoResponse.java`

`int result`, `String storageInfo`

### `com/chargedot/bluetooth/library/response/HistoryChargeRecordResponse.java`

`int totalCount`

### `com/chargedot/bluetooth/library/response/IdentityAuthResponse.java`

`String communicationVersion`, `String softwareVersion`, `String token`

### `com/chargedot/bluetooth/library/response/OcppServerConfigureResponse.java`

`int faultCauseD6`

### `com/chargedot/bluetooth/library/response/QueryAccumulatedChargingPowerWithSolarEnergyInfoResponse.java`

`int totalEnergy`, `int totalSolarEnergy`

### `com/chargedot/bluetooth/library/response/QueryActiveSolarEnergyModeConfigurationResponse.java`

`ActiveSolarEnergyModeConfiguration data`, `int result`

### `com/chargedot/bluetooth/library/response/QueryCardResponse.java`

`List<String> cardList`

### `com/chargedot/bluetooth/library/response/QueryChargeModeResponse.java`

`String endTime`, `int mode`, `String startTime`

### `com/chargedot/bluetooth/library/response/QueryChargeQuantityResponse.java`

`double chargeQuantity`

### `com/chargedot/bluetooth/library/response/QueryChargerConfigurationResponse.java`

`String content`, `int length`, `String rawContent`, `int result`, `int type`

### `com/chargedot/bluetooth/library/response/QueryChargerTcpIpConfigurationResponse.java`

`String gatewayAddress`, `String ipAddress`, `String maskAddress`, `ChargerTcpIpConfiguration.NetworkMode mode`, `String primaryDnsAddress`, `ChargerTcpIpConfiguration.NetworkType type`

### `com/chargedot/bluetooth/library/response/QueryChargingRecordsWithSolarEnergyInfoResponse.java`

`int portId`, `List<QueryChargingRecordsWithSolarEnergyInfoChargeRecord> records`

### `com/chargedot/bluetooth/library/response/QueryChargingStatusWithSolarEnergyInfoResponse.java`

`QueryChargingStatusWithSolarEnergyInfoChargingInfo chargingInfo`, `QueryChargingStatusWithSolarEnergyInfoFaultedInfo faultedInfo`, `int statusCode`, `byte[] unavailableCodes`

### `com/chargedot/bluetooth/library/response/QueryDefaultSolarEnergyModeConfigurationResponse.java`

`DefaultSolarEnergyModeConfiguration data`, `int result`

### `com/chargedot/bluetooth/library/response/QueryDeviceConfigCapacitateResponse.java`

`int config`, `int expand`

### `com/chargedot/bluetooth/library/response/QueryDeviceConfigResponse.java`

`String data`, `int deviceConfigType`, `int queryResultCode`

### `com/chargedot/bluetooth/library/response/QueryDeviceNetConfigResponse.java`

`String serverDomain`, `int serverPort`, `String tag`

### `com/chargedot/bluetooth/library/response/QueryElectricMeterConfigurationResponse.java`

`int communicateType`, `int configurationType`, `ElectricMeterConfigurationParameter electricMeterConfigurationParameters`, `String manufacturer`, `String meterPN`, `int result`, `int rtuAddress`, `int rtuBaudRate`, `int rtuCheckBit`, `int rtuDataBit`, `int rtuStopBit`, `int tcpAddress`, `int tcpGatewayAddress`, `int tcpMaskAddress`, `int tcpPort`

### `com/chargedot/bluetooth/library/response/QueryElectricMeterModbusConfigurationResponse.java`

`int communicateType`, `int modbusStatus`, `int result`, `int rtuAddress`, `int rtuBaudRate`, `int rtuCheckBit`, `int rtuDataBit`, `int rtuStopBit`, `int tcpAddress`, `int tcpGatewayAddress`, `int tcpMaskAddress`, `int tcpPort`

### `com/chargedot/bluetooth/library/response/QueryFourGModuleResponse.java`

`int CSQ`, `String IMEI`, `String IMSI`, `String apn`, `String password`, `String username`

### `com/chargedot/bluetooth/library/response/QueryIMEIResponse.java`

`String bleMac`, `String ethMac`, `String fourGIMEI`, `String fourGModemBrand`, `byte fourGSignalStrength`, `byte result`, `String sn`, `String wifiMac`

### `com/chargedot/bluetooth/library/response/QueryIOSettingsResponse.java`

`int input`, `byte inputExtra`, `int output`, `byte outputExtra`, `int result`

### `com/chargedot/bluetooth/library/response/QueryLogInfoResponse.java`

`int maxSerialNumber`, `int minSerialNumber`, `int totalCount`

### `com/chargedot/bluetooth/library/response/QueryLogListResponse.java`

`String data`

### `com/chargedot/bluetooth/library/response/QueryMaximumPhaseImbalanceResponse.java`

`boolean isSupport`, `boolean isThreePhaseElectricMeter`, `byte phaseA`, `byte phaseB`, `byte phaseC`, `int value`

### `com/chargedot/bluetooth/library/response/QueryMeterConnectStatusResponse.java`

`int masterAndModbusConnectStatus`, `int meterConnectStatus`

### `com/chargedot/bluetooth/library/response/QueryModbusResponse.java`

`BleModbus modbus`

### `com/chargedot/bluetooth/library/response/QueryPowerControlResponse.java`

`PowerControl powerControl`

### `com/chargedot/bluetooth/library/response/QuerySmartMeterResponse.java`

`SmartMeter smartMeter`

### `com/chargedot/bluetooth/library/response/QuerySolarEnergyModeOffsetConfigurationResponse.java`

`SolarEnergyModeOffsetConfiguration data`, `int result`

### `com/chargedot/bluetooth/library/response/QuerySupportsConnectionResponse.java`

`int result`, `byte[] values`

### `com/chargedot/bluetooth/library/response/QuerySysInfoResponse.java`

`String chargeFinishTime`, `String chargeMode`, `Integer chargeModeInt`, `String chargeStartTime`, `String deviceNumber`, `int deviceTime`, `String magicNumber`, `String manufacturer`, `byte[] otherInfoByte`, `String pieState`, `String plugType`, `int plugTypeRaw`, `String protocolVersion`, `int ratedCurrent`, `String softModel`, `String softVersion`, `int voice`

### `com/chargedot/bluetooth/library/response/QueryWifiInfoResponse.java`

`String password`, `String ssid`

### `com/chargedot/bluetooth/library/response/ReadStatusResponse.java`

`double chargeCurrent`, `double chargeCurrentL2`, `double chargeCurrentL3`, `int chargeDuration`, `double chargeElectricity`, `String chargeOrderSeq`, `double chargeVoltage`, `double chargeVoltageL2`, `double chargeVoltageL3`, `String faultCodes`, `int phaseLineType`, `byte[] unavailableCodes`

### `com/chargedot/bluetooth/library/response/RemoteUpgradeResponse.java`

`long currentOffset`, `int limit`, `long totalLength`

### `com/chargedot/bluetooth/library/response/ResetChargerPointResponse.java`

`int reason`, `int result`

### `com/chargedot/bluetooth/library/response/ResponseCodeEnum.java`

`int code`, `String message`

### `com/chargedot/bluetooth/library/response/SaveStorageInfoResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/ScheduledLimitResponse.java`

`boolean enableTimeRange`, `byte randomEn`, `byte randomMode`, `short randomTime`, `byte randomValid`, `List<ScheduledLimitTimeRange> ranges`, `byte result`

### `com/chargedot/bluetooth/library/response/SetConnectorTypeResponse.java`

`int result`

### `com/chargedot/bluetooth/library/response/SetWhiteListResponse.java`

`int cmd`, `int result`

### `com/chargedot/bluetooth/library/response/SmartMeterExtendedResponse.java`

`byte[] data`, `byte mode`, `byte via`

### `com/chargedot/bluetooth/library/response/SyncTimeResponse.java`

`long timestamps`

### `com/chargedot/bluetooth/library/response/VinCodeResponse.java`

`List<String> failureData`, `byte failureReason`, `byte mode`, `List<String> successData`

## All command constants from CMD.java

| Name | Decimal | Hex | Source line |
|---|---:|---|---:|
| `ACTIVE_ADD_CARD` | 208 | `0xd0` | 5 |
| `AUTH_CHARGE_CMD` | 180 | `0xb4` | 6 |
| `BEGIN_DOWNLOAD_UPGRADE_PACKAGE_CMD` | 186 | `0xba` | 7 |
| `BEGIN_UPGRADE_CMD` | 185 | `0xb9` | 8 |
| `BLUETOOTH_DEVICE_INFORMATION` | 200 | `0xc8` | 9 |
| `CE_AUTH` | 206 | `0xce` | 10 |
| `CHANGE_NET_MODE` | 212 | `0xd4` | 11 |
| `CHARGE_POINT_BASIC_INFORMATION` | 193 | `0xc1` | 12 |
| `CHARGE_POINT_EMPLOY_INFORMATION` | 194 | `0xc2` | 13 |
| `CHECK_NETWORK_STATUS` | 211 | `0xd3` | 14 |
| `CONFIGURATION_WIFI_NETWORK` | 210 | `0xd2` | 15 |
| `CONFIGURE_A7` | 167 | `0xa7` | 16 |
| `CONFIGURE_CHARGER_TCPIP_CONFIGURATION` | 171 | `0xab` | 17 |
| `CONFIGURE_ELECTRIC_METER` | 241 | `0xf1` | 18 |
| `CONFIGURE_ELECTRIC_METER_MODBUS` | 243 | `0xf3` | 19 |
| `CONFIGURE_FALLBACK` | 166 | `0xa6` | 20 |
| `CONFIGURE_IO_SETTINGS` | 245 | `0xf5` | 21 |
| `CONFIGURE_MAXIMUM_PHASE_IMBALANCE` | 162 | `0xa2` | 22 |
| `DEBUG_CHARGE_CHECK_CMD` | 50 | `0x32` | 23 |
| `DEBUG_CHECK_CHARGE_INFO_CMD` | 51 | `0x33` | 24 |
| `DEBUG_HIS_ERROR_LOG_CMD` | 52 | `0x34` | 25 |
| `DEVICE_REPORT` | 247 | `0xf7` | 26 |
| `DOWNLOADING_OCPP_SERVER_CONFIGURE` | 218 | `0xda` | 27 |
| `DOWNLOAD_OCPP_SERVER_CONFIGURE` | 217 | `0xd9` | 28 |
| `DOWNLOAD_UPGRADE_PACKAGE_SUCCESS_CMD` | 187 | `0xbb` | 29 |
| `ELECTRICAL_PROTECTION_SETTINGS` | 196 | `0xc4` | 30 |
| `FORCE_LOCK` | 231 | `0xe7` | 31 |
| `FORCE_UNLOCK` | 209 | `0xd1` | 32 |
| `GRID_NETWORK_CONFIGURATION` | 191 | `0xbf` | 33 |
| `GSM_CONFIGURATION` | 207 | `0xcf` | 34 |
| `IDENTITY_AUTHENTICATION_CMD` | 254 | `0xfe` | 35 |
| `NETWORK_OF_LAN_CONFIGURATION` | 198 | `0xc6` | 36 |
| `NETWORK_OF_WIFI_CONFIGURATION` | 199 | `0xc7` | 37 |
| `NFC_DEVICE_SETTINGS` | 201 | `0xc9` | 38 |
| `POWER_CONTROL` | 192 | `0xc0` | 39 |
| `POWER_NETWORK_LAYER_CONFIGURATION` | 195 | `0xc3` | 40 |
| `QUERY_ACCUMULATED_CHARGING_POWER_WITH_SOLAR_ENERGY_INFO` | 174 | `0xae` | 41 |
| `QUERY_CARD` | 225 | `0xe1` | 42 |
| `QUERY_CHARGER_CONFIGURATION` | 240 | `0xf0` | 43 |
| `QUERY_CHARGER_TCPIP_CONFIGURATION` | 170 | `0xaa` | 44 |
| `QUERY_CHARGE_MODE` | 230 | `0xe6` | 45 |
| `QUERY_CHARGING_RECORDS_WITH_SOLAR_ENERGY_INFO` | 173 | `0xad` | 46 |
| `QUERY_CHARGING_STATUS_WITH_SOLAR_ENERGY_INFO` | 175 | `0xaf` | 47 |
| `QUERY_DEVICE_CONFIG_CATACITATE` | 221 | `0xdd` | 48 |
| `QUERY_DEVICE_NET_CONFIG` | 219 | `0xdb` | 49 |
| `QUERY_ELECTRIC_METER_CONFIGURATION` | 242 | `0xf2` | 50 |
| `QUERY_ELECTRIC_METER_MODBUS_CONFIGURATION` | 244 | `0xf4` | 51 |
| `QUERY_FOURG_MODULE_PARAM` | 223 | `0xdf` | 52 |
| `QUERY_IMEI` | 249 | `0xf9` | 53 |
| `QUERY_IO_SETTINGS` | 246 | `0xf6` | 54 |
| `QUERY_MAXIMUM_PHASE_IMBALANCE` | 163 | `0xa3` | 55 |
| `QUERY_METER_CONNECT_STATUS` | 229 | `0xe5` | 56 |
| `QUERY_MODBUS` | 233 | `0xe9` | 57 |
| `QUERY_OCPP_SERVER_CONFIGURE_STATUS_` | 216 | `0xd8` | 58 |
| `QUERY_POWER_PERCENT` | 224 | `0xe0` | 59 |
| `QUERY_SMART_METER` | 227 | `0xe3` | 60 |
| `QUERY_SYS_LOG_INFO` | 188 | `0xbc` | 61 |
| `QUERY_SYS_LOG_LIST` | 189 | `0xbd` | 62 |
| `QUERY_WIFI_INFO` | 228 | `0xe4` | 63 |
| `READ_HISTORY_CHARGE_RECORDER_CMD` | 183 | `0xb7` | 64 |
| `READ_STATUS_CMD` | 181 | `0xb5` | 65 |
| `READ_SYS_INFO_CMD` | 177 | `0xb1` | 66 |
| `READ_TOTAL_CHARGE_CMD` | 184 | `0xb8` | 67 |
| `REQUEST_OCPP_SERVER_CONFIGURE` | 214 | `0xd6` | 68 |
| `REQUEST_OCPP_SERVER_CONFIGURE_NOTIFICATION` | 215 | `0xd7` | 69 |
| `RESET_CHARGER_POINT` | 250 | `0xfa` | 70 |
| `SCHEDULED_LIMIT` | 164 | `0xa4` | 71 |
| `SET_CHARGE_MODEL_CMD` | 179 | `0xb3` | 72 |
| `SET_DEVICE_CONFIG_CATACITATE` | 220 | `0xdc` | 73 |
| `SET_FOURG_MODULE_PARAM` | 222 | `0xde` | 74 |
| `SET_MODBUS` | 232 | `0xe8` | 75 |
| `SET_POWER_SAVING_MODE` | 160 | `0xa0` | 76 |
| `SET_SMART_METER` | 226 | `0xe2` | 77 |
| `SET_VOICE_CMD` | 178 | `0xb2` | 78 |
| `SET_WHITE_LIST` | 202 | `0xca` | 79 |
| `SMART_METER_EXTENDED` | 252 | `0xfc` | 80 |
| `SOCKET_CONFIGURATION` | 197 | `0xc5` | 81 |
| `START_ADD_CARD` | 208 | `0xd0` | 82 |
| `STOP_CHARGE_CMD` | 182 | `0xb6` | 83 |
| `SYNC_TIME_CMD` | 176 | `0xb0` | 84 |
| `VIN_CODE` | 251 | `0xfb` | 85 |

Constant names represent SDK capabilities, not proof of support by a particular device. Multiple subfunctions also share the same A7/F0 command.

## Public SDK methods (CDBleClient.java)

- Line 325: `public boolean isCmdTypeInWhiteList(int i)`
- Line 329: `public String getUpgradeFilePath()`
- Line 333: `public String getOcppFilePath()`
- Line 337: `public String getmDeviceNumber()`
- Line 341: `public int getmDeviceId()`
- Line 345: `public String getMacAddress()`
- Line 349: `public int getmUserId()`
- Line 353: `public byte[] getEncryptionKey()`
- Line 357: `public byte[] getInfo()`
- Line 361: `public boolean getEncrypted()`
- Line 365: `public int getSupportedEncryptionMode()`
- Line 369: `public String getFwVersion()`
- Line 377: `public String getSdkVersionName()`
- Line 410: `public boolean isBleEnable()`
- Line 414: `public boolean isAuthenticated()`
- Line 418: `public void init(String str, String str2, int i)`
- Line 422: `public void init(String str, String str2, int i, byte[] bArr, byte[] bArr2)`
- Line 426: `public void init(String str, String str2, int i, String str3, String str4, boolean z)`
- Line 430: `public void init(String str, String str2, int i, String str3, String str4, String str5, boolean z)`
- Line 437: `public void init(String str, String str2, int i, String str3, boolean z)`
- Line 441: `public void init(String str, String str2, int i, String str3, boolean z, byte[] bArr, byte[] bArr2)`
- Line 451: `public void setUserId(int i)`
- Line 455: `public void resume()`
- Line 463: `public void destroy()`
- Line 472: `public void search(SearchListener searchListener)`
- Line 477: `public void leSearch(LESearchListener lESearchListener)`
- Line 482: `public void stopSearch()`
- Line 488: `public void connect(ConnectListener connectListener)`
- Line 492: `public void connect(ConnectListener connectListener, BleConnectOptions bleConnectOptions)`
- Line 496: `public void connect(ConnectMode connectMode, ConnectListener connectListener)`
- Line 500: `public void connect(ConnectMode connectMode, ConnectListener connectListener, BleConnectOptions bleConnectOptions)`
- Line 611: `public void updateDeviceInfoFromScanRecord(byte[] bArr)`
- Line 673: `public ConnectMode getConnectMode()`
- Line 677: `public void syncTime(WriteListener writeListener)`
- Line 682: `public void setVoice(int i, WriteListener writeListener) throws InvalidVoiceException`
- Line 690: `public void startCharge(WriteListener writeListener)`
- Line 695: `public void stopCharge(WriteListener writeListener)`
- Line 700: `public void readStatus(WriteListener writeListener)`
- Line 705: `public void querySysInfo(WriteListener writeListener)`
- Line 710: `public void queryChargeQuantity(WriteListener writeListener)`
- Line 715: `public void timeCharge(String str, String str2, WriteListener writeListener) throws ParamIllegalException`
- Line 732: `public void setChargeMode(int i, String str, String str2, WriteListener writeListener) throws ParamIllegalException`
- Line 754: `public void queryChargeMode(WriteListener writeListener)`
- Line 759: `public void setPowerSavingMode(WriteListener writeListener)`
- Line 764: `public void remoteUpgrade(String str, String str2, String str3, WriteListener writeListener) throws ParamIllegalException, FileNotFoundException`
- Line 768: `public void remoteUpgrade(String str, String str2, String str3, WriteListener writeListener, boolean z) throws ParamIllegalException, FileNotFoundException`
- Line 789: `public void downloadUpgradePackage(int i, int i2, String str)`
- Line 795: `public void cancelUpgradeTimeoutEvent()`
- Line 799: `public void cancelRemoteUpgrade()`
- Line 808: `public void historyChargeRecord(WriteListener writeListener)`
- Line 813: `public void powerControl(PowerControl powerControl, WriteListener writeListener)`
- Line 818: `public void ceAuthentication(int i, WriteListener writeListener)`
- Line 823: `public void writeConfiguration(ConfigurationCMDEnum configurationCMDEnum, String str, WriteListener writeListener)`
- Line 828: `public void readConfiguration(ConfigurationCMDEnum configurationCMDEnum, WriteListener writeListener)`
- Line 833: `public void configurationWifiNetwork(String str, String str2, WriteListener writeListener) throws ParamIllegalException, UnsupportedEncodingException`
- Line 845: `public void checkNetworkStatus(WriteListener writeListener)`
- Line 850: `public void queryLogInfo(WriteListener writeListener)`
- Line 855: `public void queryLogList(int i, int i2, WriteListener writeListener)`
- Line 860: `public void forceUnlock(WriteListener writeListener)`
- Line 865: `public void changeNetMode(int i, WriteListener writeListener)`
- Line 870: `public void setDeviceConfigCapacitate(int i, WriteListener writeListener)`
- Line 875: `public void queryDeviceConfigCapacitate(WriteListener writeListener)`
- Line 880: `public void queryDeviceNetConfig(WriteListener writeListener)`
- Line 885: `public void ocppServerConfigure(HashMap<String, String> map, WriteListener writeListener) throws ParamIllegalException`
- Line 926: `public void downloadOcppServerConfigurePackage(int i, int i2, int i3, int i4, String str)`
- Line 930: `public void setFourGModuleParam(HashMap<String, String> map, WriteListener writeListener) throws ParamIllegalException`
- Line 941: `public void queryFourGModuleParam(WriteListener writeListener)`
- Line 946: `public void queryWifiInfo(WriteListener writeListener)`
- Line 951: `public void queryPowerPercent(WriteListener writeListener)`
- Line 956: `public void queryMeterConnectStatus(WriteListener writeListener)`
- Line 961: `public void querySmartMeter(WriteListener writeListener)`
- Line 966: `public void setSmartMeter(SmartMeter smartMeter, WriteListener writeListener) throws ParamIllegalException`
- Line 971: `public void activeAddCard(int i, WriteListener writeListener)`
- Line 976: `public void queryCard(WriteListener writeListener)`
- Line 981: `public void setModbus(BleModbus bleModbus, WriteListener writeListener)`
- Line 986: `public void queryModbus(WriteListener writeListener)`
- Line 991: `public void setWhiteList(List<String> list, WriteListener writeListener)`
- Line 996: `public void scheduledLimit(byte b, byte b2, byte b3, byte b4, short s, boolean z, List<ScheduledLimitTimeRange> list, WriteListener writeListener)`
- Line 1001: `public void addVinCode(String[] strArr, WriteListener writeListener)`
- Line 1005: `public void queryVinCode(WriteListener writeListener)`
- Line 1009: `public void deleteVinCode(String[] strArr, WriteListener writeListener)`
- Line 1018: `public void configureA7(short s, byte[] bArr, WriteListener writeListener)`
- Line 1023: `public void queryChargingStatusWithSolarEnergyInfo(int i, WriteListener writeListener)`
- Line 1028: `public void queryChargingRecordsWithSolarEnergyInfo(int i, WriteListener writeListener)`
- Line 1033: `public void queryAccumulatedChargingPowerWithSolarEnergyInfo(int i, WriteListener writeListener)`
- Line 1038: `public boolean isConnect()`
- Line 1048: `public void encryptedIdentityAuth(byte b, byte[] bArr, byte[] bArr2, byte[] bArr3, WriteListener writeListener)`
- Line 1054: `public void autoConnect()`
- Line 1059: `public void autoIdentityAuth(boolean z)`
- Line 1325: `public void autoSyncTime()`
- Line 1345: `public void queryElectricMeterModbusConfiguration(WriteListener writeListener)`
- Line 1350: `public void queryChargerConfiguration(int i, WriteListener writeListener)`
- Line 1355: `public void configureElectricMeter(int i, String str, String str2, int i2, int i3, int i4, int i5, int i6, int i7, int i8, int i9, int i10, int i11, ElectricMeterConfigurationParameter electricMeterConfigurationParameter, WriteListener writeListener)`
- Line 1360: `public void configureElectricMeterModbus(int i, int i2, int i3, int i4, int i5, int i6, int i7, int i8, int i9, int i10, WriteListener writeListener)`
- Line 1365: `public void queryElectricMeterConfiguration(WriteListener writeListener)`
- Line 1370: `public void configureIOSettings(int i, byte b, int i2, byte b2, WriteListener writeListener)`
- Line 1375: `public void configureFallback(byte b, short s, WriteListener writeListener)`
- Line 1380: `public void queryIOSettings(WriteListener writeListener)`
- Line 1385: `public void resetChargerPoint(int i, int i2, WriteListener writeListener)`
- Line 1390: `public void configureMaximumPhaseImbalance(boolean z, byte b, byte b2, byte b3, byte b4, boolean z2, WriteListener writeListener)`
- Line 1395: `public void queryMaximumPhaseImbalance(WriteListener writeListener)`
- Line 1400: `public void smartMeterExtended(byte b, byte b2, byte[] bArr, WriteListener writeListener)`
- Line 1405: `public void queryIMEI(WriteListener writeListener)`
- Line 1410: `public void configureDefaultSolarEnergyMode(DefaultSolarEnergyModeConfiguration defaultSolarEnergyModeConfiguration, WriteListener writeListener)`
- Line 1421: `public void queryDefaultSolarEnergyModeConfiguration(WriteListener writeListener)`
- Line 1426: `public void configureActiveSolarEnergyMode(ActiveSolarEnergyModeConfiguration activeSolarEnergyModeConfiguration, WriteListener writeListener)`
- Line 1437: `public void queryActiveSolarEnergyModeConfiguration(WriteListener writeListener)`
- Line 1442: `public void configureSolarEnergyModeOffset(SolarEnergyModeOffsetConfiguration solarEnergyModeOffsetConfiguration, WriteListener writeListener)`
- Line 1453: `public void queryChargerTcpIpConfiguration(ChargerTcpIpConfiguration.NetworkType networkType, WriteListener writeListener)`
- Line 1458: `public void configureChargerTcpIpConfiguration(ChargerTcpIpConfiguration chargerTcpIpConfiguration, WriteListener writeListener)`
- Line 1469: `public void saveStorageInfo(String str, WriteListener writeListener)`
- Line 1480: `public void getStorageInfo(WriteListener writeListener)`
- Line 1485: `public void configureSupportsConnectionModes(byte[] bArr, WriteListener writeListener)`
- Line 1490: `public void querySupportsConnectionModes(WriteListener writeListener)`
- Line 1495: `public void forceLock(WriteListener writeListener)`
- Line 1592: `public void configDeviceConfigType(int i, String str, WriteListener writeListener)`
- Line 1615: `public void queryDeviceConfigType(int i, WriteListener writeListener)`
- Line 1657: `public void refreshCache()`
- Line 1661: `public void setOnDeviceReportListener(DeviceReportListener deviceReportListener)`
- Line 1665: `public void setConnectDetailListener(ConnectDetailListener connectDetailListener)`
- Line 1669: `public void setOnConnectFailureListener(ConnectFailureListener connectFailureListener)`
- Line 1673: `public void setCommandLogListener(CommandLogListener commandLogListener)`

## App wrapper (AbbBluetoothClient.java)

- Line 215: `public final CDBleClient getBleClient()`
- Line 219: `public final AbbConnectionListener getAbbConnectionListener()`
- Line 223: `public final void setAbbConnectionListener(AbbConnectionListener abbConnectionListener)`
- Line 227: `public final Function0<Unit> getOnFirmwareUpdateRequired()`
- Line 231: `public final void setOnFirmwareUpdateRequired(Function0<Unit> function0)`
- Line 235: `public final boolean isBleEnable()`
- Line 239: `public final boolean isConnected()`
- Line 248: `public final int getConnectedDeviceId()`
- Line 252: `public final String getConnectedDeviceMacAddress()`
- Line 258: `public final ConnectMode getConnectMode()`
- Line 264: `public final int getMDeviceId()`
- Line 268: `public final void setMDeviceId(int i)`
- Line 272: `public final String getMDeviceNumber()`
- Line 276: `public final void setMDeviceNumber(String str)`
- Line 281: `public final Integer getPreviousDeviceId()`
- Line 285: `public final void setPreviousDeviceId(Integer num)`
- Line 289: `public final Pair<ConnectMode, Integer> getPreviousStatus()`
- Line 293: `public final void setPreviousStatus(Pair<? extends ConnectMode, Integer> pair)`
- Line 299: `public final boolean getIsSearching()`
- Line 303: `public final void setSearching(boolean z)`
- Line 308: `public final boolean getIsConnecting()`
- Line 312: `public final void setConnecting(boolean z)`
- Line 317: `public final boolean getIsBluetoothRetried()`
- Line 321: `public final void setBluetoothRetried(boolean z)`
- Line 326: `public final boolean getIsWebsocketRetried()`
- Line 330: `public final void setWebsocketRetried(boolean z)`
- Line 334: `public final List<DeviceSettingsSection> getDeviceSettingsSectionList()`
- Line 338: `public final void setDeviceSettingsSectionList(List<? extends DeviceSettingsSection> list)`
- Line 343: `public final String getFirmwareVersion()`
- Line 349: `public final StateFlow<Boolean> getCableReleaseSupported()`
- Line 357: `public final StateFlow<Boolean> getLocalControllerConfigured()`
- Line 366: `public final void handleWebSocketDisconnect()`
- Line 382: `public final void handleBluetoothDisconnect()`
- Line 408: `public final void searchBluetoothDevicesWithListener(Long duration, final Function0<Unit> onCancel, LESearchListener searchListener)`
- Line 431: `public final void stopSearchForBluetoothDevices()`
- Line 436: `public final void initDeviceConnection(String macAddress, String deviceNumber, int deviceId, String email, String token)`
- Line 454: `public final void initBluetoothConnection(final String macAddress, final String deviceNumber, final int deviceId, final boolean autoConnect)`
- Line 592: `public final void fetchCipher(int deviceId, String deviceNumber, Function1<? super SecureCipher, Unit> onResult)`
- Line 618: `public final void connectBluetoothDevice(String macAddress)`
- Line 645: `public final void connectRemoteControl()`
- Line 668: `public final void queryELockStatus(final Function1<? super Integer, Unit> onSuccess)`
- Line 686: `public final void forceLock(final Function0<Unit> onSuccess, final Function0<Unit> onError)`
- Line 721: `public final void forceUnlock(final Function0<Unit> onError, final Function0<Unit> onSuccess)`
- Line 743: `public final void querySystemInfo(AbbBluetoothResultListener<QuerySysInfoResponse> listener)`
- Line 748: `public final void readNetworkStatus(AbbBluetoothResultListener<CheckNetworkStatusResponse> listener)`
- Line 753: `public final void writeWiFiConfiguration(String ssid, String password, AbbBluetoothResultListener<ConfigurationWifiNetworkResponse> listener) throws ParamIllegalException, UnsupportedEncodingException`
- Line 760: `public final void readWiFiConfiguration(AbbBluetoothResultListener<QueryWifiInfoResponse> listener)`
- Line 765: `public final void disableConnections(AbbBluetoothResultListener<CEAuthenticationResponse> listener)`
- Line 770: `public final void enableEthernet(AbbBluetoothResultListener<CEAuthenticationResponse> listener)`
- Line 775: `public final void enableWiFi(AbbBluetoothResultListener<CEAuthenticationResponse> listener)`
- Line 780: `public final void enableMobileConnection(AbbBluetoothResultListener<CEAuthenticationResponse> listener)`
- Line 785: `public final void readDeviceConfiguration(AbbBluetoothResultListener<QueryDeviceConfigCapacitateResponse> listener)`
- Line 790: `public final void readDeviceConfigurationWithParams(int type, AbbBluetoothResultListener<QueryChargerConfigurationResponse> listener)`
- Line 795: `public final void readSchedule(AbbBluetoothResultListener<QueryChargeModeResponse> listener)`
- Line 800: `public final void setSchedule(String startTime, String endTime, final AbbBluetoothResultListener<QueryChargeModeResponse> listener) throws ParamIllegalException`
- Line 820: `public final void disableSchedule(AbbBluetoothResultListener<SetChargeModeResponse> listener) throws ParamIllegalException`
- Line 825: `public final void enableOrDisableFreeVending(final boolean isEnabled, final AbbBluetoothResultListener<QueryDeviceConfigCapacitateResponse> listener)`
- Line 895: `public final Object getModbusConfiguration(Continuation<? super Unit> continuation)`
- Line 950: `public final void readChargingStatus(AbbBluetoothResultListener<ReadStatusResponse> listener)`
- Line 955: `public final void readChargingStatusWithSolar(AbbBluetoothResultListener<QueryChargingStatusWithSolarEnergyInfoResponse> listener)`
- Line 960: `public final void readChargingStatus(final Function1<? super String, Unit> onError, final Function1<? super ChargerStatus, Unit> onSuccess)`
- Line 992: `public final void startCharging(AbbBluetoothResultListener<StartChargeResponse> listener)`
- Line 997: `public final void setCountrySpecificSchedules(List<? extends ScheduledLimitTimeRange> schedules, short randomDelay, final AbbBluetoothResultListener<ScheduledLimitResponse> listener)`
- Line 1012: `public final void skipDelayedCharging(final AbbBluetoothResultListener<ScheduledLimitResponse> listener)`
- Line 1072: `public final void handleLoadBalancingPlanResponse(List<? extends ScheduledLimitTimeRange> schedules, List<? extends ScheduledLimitTimeRange> schedulesToAdd, final List<? extends ScheduledLimitTimeRange> schedulesToRemove, final List<? extends ScheduledLimitTimeRange> countrySpecificSchedules, final AbbBluetoothResultListener<ScheduledLimitResponse> listener, Function1<? super ScheduledLimitTimeRange[], Unit> onOverlap, MaterialAlertDialogBuilder onCountrySpecificOverwrittenDialog)`
- Line 1206: `public final void updateLoadBalancingPlan(final List<? extends ScheduledLimitTimeRange> schedulesToAdd, final List<? extends ScheduledLimitTimeRange> schedulesToRemove, final List<? extends ScheduledLimitTimeRange> countrySpecificSchedules, final AbbBluetoothResultListener<ScheduledLimitResponse> listener, final Function1<? super ScheduledLimitTimeRange[], Unit> onOverlap, final MaterialAlertDialogBuilder onCountrySpecificOverwrittenDialog)`
- Line 1246: `public final void scheduledLimit(byte mode, boolean enableTimeRange, List<? extends ScheduledLimitTimeRange> data, WriteListener<ScheduledLimitResponse> listener)`
- Line 1261: `public final void setNewLoadBalancingPlan(final List<? extends ScheduledLimitTimeRange> schedulesToAdd, final List<? extends ScheduledLimitTimeRange> countrySpecificSchedules, final AbbBluetoothResultListener<ScheduledLimitResponse> listener, final Function1<? super ScheduledLimitTimeRange[], Unit> onOverlap, final MaterialAlertDialogBuilder onCountrySpecificOverwrittenDialog)`
- Line 1285: `public final void deleteLoadBalancingPlan(final List<? extends ScheduledLimitTimeRange> schedulesToRemove, final AbbBluetoothResultListener<ScheduledLimitResponse> listener)`
- Line 1326: `public final void readLoadBalancingPlans(AbbBluetoothResultListener<ScheduledLimitResponse> listener)`
- Line 1331: `public final void stopCharging(AbbBluetoothResultListener<StopChargeResponse> listener)`
- Line 1336: `public final void readChargeSessions(AbbBluetoothResultListener<HistoryChargeRecordResponse> listener)`
- Line 1341: `public final void readChargeSessionsWithSolar(AbbBluetoothResultListener<QueryChargingRecordsWithSolarEnergyInfoResponse> listener)`
- Line 1346: `public final void readPowerPercent(AbbBluetoothResultListener<QueryPowerControlResponse> listener)`
- Line 1351: `public final void readMobileConnectionParams(AbbBluetoothResultListener<QueryFourGModuleResponse> listener)`
- Line 1369: `public final void writeMobileConnectionParams(boolean isAuto, String apn, String username, String password, AbbBluetoothResultListener<SetFourGModuleResponse> listener) throws ParamIllegalException`
- Line 1383: `public final void readRFIDCards(AbbBluetoothResultListener<QueryCardResponse> listener)`
- Line 1388: `public final void addRFIDCards(int duration, AbbBluetoothResultListener<ActiveAddCardResponse> listener)`
- Line 1393: `public final void deleteRfidCards(final List<String> cardsToDelete, final AbbBluetoothResultListener<SetWhiteListResponse> listener)`
- Line 1420: `public final void startRemoteUpgrade(String version, String checkSum, String filePath, final AbbBluetoothResultListener<RemoteUpgradeResponse> listener, boolean registerListenerOnly) throws ParamIllegalException, FileNotFoundException`
- Line 1441: `public final void cancelRemoteUpgrade()`
- Line 1445: `public final void readSolarEnergyConfiguration(AbbBluetoothResultListener<QueryDefaultSolarEnergyModeConfigurationResponse> listener)`
- Line 1450: `public final void readActiveSolarEnergyMode(AbbBluetoothResultListener<QueryActiveSolarEnergyModeConfigurationResponse> listener)`
- Line 1455: `public final void switchSessionEnergyMode(ChargingMode mode, AbbBluetoothResultListener<ConfigureActiveSolarEnergyModeResponse> listener)`
- Line 1461: `public final void configureDefaultSolarEnergyMode(DefaultSolarEnergyModeConfiguration chargingModeConfiguration, AbbBluetoothResultListener<ConfigureDefaultSolarEnergyModeResponse> listener)`
- Line 1467: `public final void readStorageInfo(AbbBluetoothResultListener<GetStorageInfoResponse> listener)`
- Line 1472: `public final void saveStorageInfo(String storageInfo, AbbBluetoothResultListener<SaveStorageInfoResponse> listener)`
- Line 1478: `public final void writeTcpIpConfiguration(ChargerTcpIpConfiguration params, AbbBluetoothResultListener<ConfigureChargerTcpIpConfigurationResponse> listener)`
- Line 1484: `public final void readTcpIpConfiguration(ChargerTcpIpConfiguration.NetworkType type, AbbBluetoothResultListener<QueryChargerTcpIpConfigurationResponse> listener)`
- Line 1490: `public final void readChargerConfiguration(short type, AbbBluetoothResultListener<QueryChargerConfigurationResponse> listener)`
- Line 1495: `public final void disconnect()`
- Line 1508: `public final void destroy(boolean isSwitching)`
- Line 1523: `public final void writePowerControl(PowerControl powerControl, AbbBluetoothResultListener<PowerControlResponse> listener)`
- Line 1529: `public final void querySmartMeter(AbbBluetoothResultListener<QuerySmartMeterResponse> listener)`
- Line 1534: `public final void queryElectricMeter(AbbBluetoothResultListener<QueryElectricMeterConfigurationResponse> listener)`
- Line 1539: `public final void queryDeviceLogInfo(AbbBluetoothResultListener<QueryLogInfoResponse> listener)`
- Line 1544: `public final void queryDeviceLogsList(int from, int limit, AbbBluetoothResultListener<QueryLogListResponse> listener)`
- Line 1575: `public final int[] intToBitArray(int intSource)`
- Line 1674: `public final <T> Object suspendCancellableCoroutineWithTimeout(long j, Function1<? super CancellableContinuation<? super T>, Unit> function1, Continuation<? super T> continuation)`
- Line 1679: `public final <T extends CDBleResponse> WriteListener<T> abbWriteListener(final AbbBluetoothResultListener<T> listener)`
- Line 1721: `public final <T extends CDBleResponse> AbbBluetoothResultListener<T> abbWriteListener(final Function1<? super T, Unit> onError, final Function1<? super T, Unit> onSuccess)`
- Line 1753: `public final void checkAndUpdateAvailableSettingTabs(Charger connectedCharger)`
- Line 1764: `public final void removeAllConnectHandlerMessages()`
- Line 1769: `public final void resetRetries()`
- Line 1786: `public final Object waitForConnection(long j, long j2, Function0<Unit> function0, final Function0<Unit> function1, Continuation<? super Unit> continuation)`
- Line 1838: `public final Object getModbusConfig(Function1<? super String, Unit> function1, Continuation<? super BleModbus> continuation)`

## App screens

- `addcharger/changename/ChangeNameFragment.java`
- `addcharger/connections/ConnectionsFragment.java`
- `addcharger/connecttocharger/ConnectToChargerFragment.java`
- `addcharger/enterpin/EnterPinFragment.java`
- `addcharger/enterpin/ScanProductFragment.java`
- `addcharger/enterpin/ScannerFragment.java`
- `addcharger/selectcountry/SelectCountryFragment.java`
- `base/AppBaseBindingVMFragment.java`
- `base/AppBaseVMFragment.java`
- `base/BaseBluetoothFragment.java`
- `base/BottomSheetDialogBindingVMFragment.java`
- `base/BottomSheetDialogVMFragment.java`
- `bottom_sheet_modal/estimated_cost/EstimatedCostBottomSheetDialogFragment.java`
- `bottom_sheet_modal/feedback_rating/FeedbackRatingBottomSheetDialogFragment.java`
- `chargerdetail/ChargerDetailFragment.java`
- `chargerdetail/editcharger/EditChargerFragment.java`
- `customnavigation/AbbNavHostFragment.java`
- `deleteaccount/chargers/DeleteAccountChargersFragment.java`
- `deleteaccount/info/DeleteAccountInfoFragment.java`
- `deleteaccount/success/DeleteAccountSuccessFragment.java`
- `login/LoginFragment.java`
- `login/forgotpassword/ResetPasswordCodeFragment.java`
- `login/forgotpassword/ResetPasswordEmailFragment.java`
- `login/forgotpassword/ResetPasswordFragment.java`
- `login/register/RegisterFragment.java`
- `login/register/RegisterSuccessFragment.java`
- `main/appsettings/AppSettingsFragment.java`
- `main/appsettings/changepassword/ChangePasswordFragment.java`
- `main/carcapacity/CarCapacityFragment.java`
- `main/chargers/ChargersFragment.java`
- `main/dashboard/DashboardFragment.java`
- `main/dashboard/charging/ChargingFragment.java`
- `main/dashboard/charging/confirmcountry/ConfirmCountryFragment.java`
- `main/dashboard/charging/summary/SessionSummaryFragment.java`
- `main/dashboard/schedule/ScheduleFragment.java`
- `main/dashboard/statistics/StatisticsFragment.java`
- `main/dashboard/statistics/detail/StatisticsDetailFragment.java`
- `main/dashboard/statistics/detail/activities/ActivitiesFragment.java`
- `main/dashboard/statistics/detail/activities/detail/ActivityFragment.java`
- `main/dashboard/statistics/detail/graphs/GraphFragment.java`
- `main/dashboard/statistics/export/ExportStatisticsFragment.java`
- `main/dashboard/statistics/export/auto/AutoExportFragment.java`
- `main/devicesettings/DeviceSettingsFragment.java`
- `main/devicesettings/cableStuck/CableStuckFragment.java`
- `main/devicesettings/changenetwork/ChangeNetworkFragment.java`
- `main/devicesettings/chargingMode/ChargingModeFragment.java`
- `main/devicesettings/chargingMode/identifygridmeter/selectModel/SelectModelFragment.java`
- `main/devicesettings/chargingMode/identifygridmeter/selectSeries/SelectSeriesFragment.java`
- `main/devicesettings/chargingMode/identifygridmeter/selectSubModel/SelectSubModelFragment.java`
- `main/devicesettings/energyplan/EnergyPlanFragment.java`
- `main/devicesettings/firmwareupdate/FirmwareUpdateFragment.java`
- `main/devicesettings/firmwareupdate/rebootingcharger/RebootingChargerFragment.java`
- `main/devicesettings/freevending/FreeVendingFragment.java`
- `main/devicesettings/loadbalance/LoadBalanceFragment.java`
- `main/devicesettings/log/LogFragment.java`
- `main/devicesettings/support/SupportFragment.java`
- `main/share/addcard/AddCardFragment.java`
- `main/share/carddetails/CardDetailsFragment.java`
- `search_country/SearchCountriesFragment.java`
- `search_country/region/SearchRegionFragment.java`

## Integrity

XAPK SHA-256: `2422cc8f647639313b1657879ec25b0cd74265b1ac8ae355bef2084d5c4262a0`

60 REST declarations; 58 unique method/path combinations; 81 command names; 80 unique command numbers.
