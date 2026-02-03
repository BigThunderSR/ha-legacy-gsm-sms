# Changelog

All notable changes to this project will be documented in this file.

## [2.18.3] - 2026-02-02

### Fixed

- **Post-Call Cooldown Period** ⏱️
  - Added 10-second cooldown after call ends before resuming modem operations
  - Modem needs recovery time after handling incoming calls
  - Prevents timeout errors when SMS poll runs immediately after ring timeout
  - Logs "Post-call cooldown complete, resuming SMS monitoring" when ready

### Changed

- **Faster Missed Call Detection** 📞
  - Reduced ring timeout from 30s to 10s for faster missed call detection
  - Rings typically come every 5-6 seconds, so 10s gap = call ended
  - Missed call sensor now updates ~20 seconds sooner

## [2.18.2] - 2026-02-02

### Fixed

- **Prevent Modem Timeouts During Incoming Calls** 📶
  - Pause SMS polling and periodic status updates while phone is ringing
  - Prevents `retrieveAllSms` timeout errors during active incoming calls
  - ReadDevice loop for call monitoring now has exclusive modem access during calls
  - Eliminates unnecessary modem restarts caused by concurrent operations

## [2.18.1] - 2026-02-02

### Fixed

- **Missed Call Detection via Ring Timeout** 📞
  - Added 30-second ring timeout mechanism for missed call detection
  - Fixes issue where calls going to voicemail weren't detected as missed
  - Some modems don't send CallRemoteEnd when caller hangs up or goes to voicemail
  - Ring timeout now properly triggers missed call sensor update
  - New attribute `detected_by: ring_timeout` indicates timeout-based detection

- **Fixed setupCallbacks return keys**
  - Corrected key mismatch between `setupCallbacks()` and `start_callback_monitoring()`
  - Was returning `{'calls', 'sms'}`, now returns `{'incoming_call', 'incoming_sms'}`

## [2.18.0] - 2026-02-02

### Added

- **Real-time Call Monitoring** 📞 (Based on upstream PavelVe v1.6.0)
  - Detect incoming calls and missed calls in real-time via Gammu callbacks
  - New binary sensor: **Incoming Call** - shows live ringing state
    - State: ON = ringing, OFF = not ringing
    - Attributes: Number, ring_start, ring_count
  - New sensor: **Last Missed Call** - shows missed call details
    - State: caller phone number
    - Attributes: ring_start, ring_end, ring_duration_seconds, ring_count
  - Works on most modems with CLIP support (SIM800L, Huawei, Quectel, etc.)
  - New config option: `missed_calls_monitoring_enabled` (default: false)

- **SMS Callback Support** 📨
  - Faster SMS delivery via Gammu callbacks
  - 3-second debounce for multi-part SMS
  - Polling remains as fallback for unsupported modems

- **ReadDevice Loop** 🔄
  - Background thread polls modem for callback events every 1 second
  - Only runs when call or SMS callbacks are supported

### Changed

- Added `setupCallbacks()` function to support.py for Gammu callback setup
- Enhanced MQTT discovery with call monitoring sensors (when enabled)

## [2.17.6] - 2026-01-12

### Fixed

- **Critical: MMS notification crash protection** 🛡️
  - Added robust SMS decoding with fallback for binary/corrupted messages
  - Prevents addon crash when receiving MMS notifications
  - DELETE ALL endpoint now works even with MMS on SIM card
  - Safely handles UnicodeDecodeError with error replacement
  - Based on upstream PavelVe v1.5.7 fix

- **Flask-RESTX authentication error handling** 🔐
  - Fixed marshalling errors on unauthenticated requests
  - Proper 401 responses instead of MarshallingError
  - Added `code=200` parameter to all `@marshal_with` decorators
  - Based on upstream PavelVe v1.5.7 fix

## [2.17.5] - 2026-01-09

### Improved

- **Swagger UI GET endpoint positioning** 📋
  - Added `/sms/add/{sms_data}` route alias for better Swagger UI discoverability
  - New route appears right after POST /sms and GET /sms in API documentation
  - Original `/sms/{sms_data}` route preserved for backward compatibility with legacy devices
  - Both routes point to same endpoint - no functionality changes
  - Updated Swagger documentation with clearer examples and available paths

## [2.17.4] - 2026-01-08

### Improved

- **Swagger UI endpoint organization** 📋
  - Reorganized endpoint order for better UX and discoverability
  - GET /sms/{sms_data} (send via GET) now appears immediately after POST /sms
  - Both SMS sending endpoints are now grouped together logically
  - Individual SMS operations (GET/DELETE by ID) moved to end of SMS section
  - New order: Send (POST) → Send (GET) → List → Delete All → Operations by ID

## [2.17.3] - 2026-01-08

### Fixed

- **Swagger parameter format** 🔧
  - Simplified GET endpoint parameter to use Swagger 2.0 compatible single example
  - Parameter now shows default value: `5555551234&Test+message`
  - Improved compatibility with Flask-RESTX/Swagger UI
  - Execute button works correctly for testing endpoint

## [2.17.2] - 2026-01-08

### Improved

- **Enhanced Swagger API documentation** 📖
  - Added comprehensive GET endpoint documentation with emoji sections
  - Documented all security features (IP whitelisting, optional auth, deduplication)
  - Added practical examples with different URL encoding scenarios
  - Documented configuration options with default values
  - Added usage notes and best practices
  - Updated home page endpoint list to include new GET endpoint

## [2.17.1] - 2026-01-08

### Added

- **Comprehensive test suite** 🧪
  - Added 21 automated tests for GET endpoint functionality
  - Tests cover IP whitelisting, URL decoding, deduplication, config defaults, and path parsing
  - Integrated into CI/CD pipeline for automated validation

## [2.17.0] - 2026-01-08

### Added

- **GET endpoint for SMS sending** 🆕
  - New GET endpoint for legacy system compatibility
  - Format: `GET /sms/{PHONE_NUMBER}&{MESSAGE}`
  - Example: `GET /sms/5555551234&Your+message+here`
  - Automatic URL decoding and Unicode detection
  - Ideal for devices that only support GET requests
- **GET endpoint security controls** 🔒
  - `get_endpoint_auth_required`: Toggle authentication requirement (default: false for legacy compatibility)
  - `get_endpoint_allowed_ips`: IP whitelist using CIDR notation
  - Default whitelist: `192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`, `127.0.0.1`
  - Blocks requests from unauthorized IPs with 403 error
  - Optionally require HTTP Basic Auth for GET endpoint

### Fixed

- **GET endpoint SMS encoding** 🐛
  - Fixed incorrect call to `encodeSms()` function that caused "unexpected keyword argument 'unicode'" error
  - GET endpoint now properly constructs smsinfo dict matching POST endpoint behavior
  - Resolves issue where GET requests would fail with encoding errors
- **REST API now accepts form-encoded requests** 📝
  - Added support for `application/x-www-form-urlencoded` Content-Type
  - API now accepts both JSON and form-encoded data for SMS sending
  - Enables integration with applications that can't send JSON or custom headers
  - Example: `curl -d "number=+1234&message=test" http://admin:pass@host:5000/sms`
  - Fixes 415 Unsupported Media Type error when sending form data

## [2.16.0] - 2025-12-21

### ⚠️ BREAKING CHANGES

- **Balance sensors now use numeric values instead of strings**
  - `sensor.sms_gateway_data_remaining`: Changed from `"200.00 MB"` to `200.0` (numeric)
  - `sensor.sms_gateway_account_balance`: Changed from `"$3.00"` to `3.0` (numeric)
  - **Migration:** If you have automations using these sensors with string comparisons or templates expecting the unit in the value, you'll need to update them
  - Existing saved balance data is automatically migrated to the new format on first load

### Added

- **Proper Home Assistant sensor device classes** 🏷️
  - `sensor.sms_gateway_signal_dbm`: Already had `device_class: signal_strength` ✓
  - `sensor.sms_gateway_sent_count`: Added `unit_of_measurement: messages`
  - `sensor.sms_gateway_received_count`: Added `unit_of_measurement: messages`
  - `sensor.sms_gateway_total_cost`: Added `device_class: monetary`
  - `sensor.sms_gateway_minutes_remaining`: Added `device_class: duration`
  - `sensor.sms_gateway_plan_expiry`: Added `device_class: date`
  - `sensor.sms_gateway_data_remaining`: Added `device_class: data_size`, `state_class: measurement`, `unit: MB`
  - `sensor.sms_gateway_account_balance`: Added `device_class: monetary`, `state_class: total`

- **New configuration option: `balance_currency`** 💰
  - ISO 4217 currency code for account balance display (default: `USD`)
  - Examples: `USD`, `EUR`, `GBP`, `CZK`, `PLN`
  - Used for the `unit_of_measurement` of the account balance sensor

### Improved

- **Better Home Assistant integration**
  - Sensors now support proper statistics and graphs
  - Unit conversions work correctly (HA can convert MB to GB, etc.)
  - Currency display follows HA's localization settings
  - Duration sensor formats nicely in HA UI

### Technical

- Balance parser now stores numeric values with separate unit fields
- Added `_migrate_old_format()` method for backward compatibility with saved data
- Added translations for `balance_currency` in all 10 supported languages

## [2.15.4] - 2025-12-17

### Fixed

- **Fixed ThreadPoolExecutor blocking on timeout** 🐛
  - Root cause: Using `with ThreadPoolExecutor() as executor:` context manager calls `shutdown(wait=True)` on exit
  - When a 15s Python timeout occurred, the exception was raised but the context manager's `__exit__` blocked waiting for the underlying Gammu thread to complete (which could take 9+ minutes)
  - Changed from context manager to manual executor management with `shutdown(wait=False)`
  - Now when a timeout occurs, the function returns immediately without waiting for the hung thread
  - This ensures restart timer is checked every 10 seconds and addon restarts within ~30-45 seconds of modem freeze

- **Fixed `seconds_since_last_success` sensor not updating when modem offline** 🐛
  - When in hard_offline state, the loops were skipping modem operations but also not publishing device status
  - Now `publish_device_status()` is called in both SMS monitoring and status publishing loops even during hard_offline
  - This keeps the `seconds_since_last_success` sensor updating in real-time while offline

## [2.15.3] - 2025-12-17

### Fixed

- **Fixed race condition in hard_offline check** 🐛
  - Added hard_offline check inside `track_gammu_operation` AFTER acquiring the gammu_lock
  - Previously, threads would check hard_offline, then wait for lock, then proceed even if another thread set hard_offline while waiting
  - Now operations are skipped immediately after acquiring lock if hard_offline is set
  - This eliminates the 4+ minute delays caused by queued operations

## [2.15.2] - 2025-12-16

### Fixed

- **Fixed restart timer blocked by hung modem operations** 🐛
  - When modem is in hard_offline state (completely frozen), skip ALL modem operations
  - SMS monitoring loop: Skip modem ops at top of loop, check restart timer, sleep 10s
  - Status publishing loop: Skip modem ops at top of loop, also check between GetSignalQuality and GetNetworkInfo
  - Previously each blocked operation added 15+ seconds delay before restart
  - Restart now triggers within ~45 seconds (best case) to ~50 seconds (worst case)

## [2.15.1] - 2025-12-16

### Fixed

- **Fixed restart timer not being checked repeatedly after initial timeout** 🐛
  - The restart timer was only checked once at the moment of timeout
  - Subsequent SMS monitoring cycles didn't re-check the timer
  - Now `_check_restart_timeout()` is called on every failed SMS monitoring cycle
  - Addon will correctly restart after `hard_offline_restart_timeout` seconds

## [2.15.0] - 2025-12-16

### Added

- **New configuration option: `hard_offline_restart_timeout`** ⚙️
  - Configurable timeout (10-120 seconds) before restart when modem times out completely
  - Default: 30 seconds (vs. 120s for normal failures)
  - Faster recovery from frozen modem state

### Fixed

- **Fixed modem not being marked offline on SMS operation timeout** 🐛
  - When `retrieveAllSms` timed out after 15s, the modem stayed "online" because:
    - The offline threshold required 2+ consecutive failures
    - Status polling (`GetSignalQuality`) would succeed and reset the failure counter
  - Added `hard_offline` state that is set immediately on timeout errors
  - Status polling can no longer clear `hard_offline` - only SMS operations can
  - New MQTT status fields: `hard_offline` (boolean), `hard_offline_operation` (string)
  - Modem now correctly shows "offline" when SMS operations are timing out

- **Fixed auto-restart not triggering when modem is in hard offline state** 🐛
  - The restart timer was being reset by successful status polling (GetSignalQuality)
  - Now the restart timer persists through status polls when in `hard_offline` state
  - Addon will correctly restart after timeout threshold is reached

## [2.14.0] - 2025-12-15

### Added

_Features synced from [PavelVe/hassio-addons](https://github.com/PavelVe/hassio-addons) upstream (v1.5.4-v1.5.5)_

- **Flash SMS Support (Class 0 Messages)** ⚡
  - Flash SMS displays immediately on recipient's phone screen without being saved
  - New "Send Flash SMS" button entity in Home Assistant
  - Support for `flash: true` parameter in MQTT send command payload
  - Support for `flash: true` parameter in REST API `/sms` endpoint
  - Ideal for urgent alerts and notifications
  - Note: Not all phones/carriers support Flash SMS

- **Multiple Recipients via MQTT** 📱
  - MQTT SMS sending now supports comma-separated phone numbers
  - Example: `{"number": "+1234567890,+0987654321", "text": "Hello"}`
  - SMS counter increments correctly for each recipient
  - Matches REST API behavior for consistency

- **Raspberry Pi 5 Serial Port Support** 🍓
  - Added `/dev/ttyAMA0` and `/dev/ttyAMA1` to supported device paths
  - Enables native serial port support on Raspberry Pi 5

### Fixed

- **Phone Number Field Validation** 📞
  - Updated phone number input pattern to allow comma separator
  - Enables entering multiple recipients in Home Assistant UI (e.g., `+123,+456`)

## [2.13.2] - 2025-12-03

### Fixed

- **Fixed REST API Unicode auto-detection not triggering** 🐛
  - Removed `data.setdefault('unicode', False)` which was overriding auto-detection
  - Changed parser default from `False` to `None` to allow auto-detection
  - Emoji/special characters now correctly auto-detected via REST API

## [2.13.1] - 2025-12-03

### Fixed

- **REST API now auto-detects Unicode mode for SMS** 🐛
  - Fixed emoji/special characters being sent as `??` via REST API actions
  - REST API now matches MQTT behavior: auto-detects Unicode when not explicitly set
  - If `unicode` parameter is omitted, checks if text contains non-ASCII characters
  - Explicitly setting `unicode: true/false` still honored for manual control

## [2.13.0] - 2025-12-03

### Changed

- **Network type detection now reconnect-only by default** 🔧
  - `network_type_cache_seconds` default changed from 300 to 0
  - Value of 0 means network type (2G/3G/4G) is only checked on modem reconnection
  - This avoids the disruptive Gammu disconnect/reconnect cycle during periodic updates
  - Helps prevent modem crashes on sensitive hardware like SIM7600
  - Set to 1-3600 for periodic refresh if needed (not recommended for unstable modems)

## [2.12.0] - 2025-12-02

### Added

- **Configurable modem operation delay** 🆕
  - New `modem_operation_delay` config option (default: 0.3 seconds)
  - Adds delay between sequential modem commands to prevent buffer overflow
  - Range: 0.1 to 5.0 seconds
  - Helps prevent crashes on modems like SIM7600 and Huawei E1750
  - Recommended: 0.5-1.0s for SIM7600 series experiencing frequent disconnects

## [2.11.0] - 2025-12-01

### Added

- **MQTT-based SMS queuing for addon restart resilience** 🆕
  - New `queue_sms` MQTT topic with retained messages
  - SMS requests persist in MQTT broker even when addon is down
  - When addon restarts, picks up retained messages and queues them
  - Use `mqtt.publish` to `homeassistant/sensor/sms_gateway/queue_sms` with `retain: true`
  - Payload: `{"number": "...", "text": "..."}` (same as `/send` topic)
  - Complements REST API for scenarios where addon may be unavailable

## [2.10.4] - 2025-11-29

### Fixed

- **SMS lost during restart if sent via REST API** 🐛
  - SMS was not persisted to queue before send attempt
  - If addon restarted during send/retry, SMS would be lost
  - Now queues SMS BEFORE attempting to send
  - On success, removes from queue; on failure, remains queued
  - Survives restarts during any phase of send operation

## [2.10.3] - 2025-11-29

### Fixed

- **Improved error code extraction from Gammu exceptions** 🐛
  - Added fallback string parsing for error codes when dict extraction fails
  - Added debug logging to diagnose extraction failures
  - Now handles edge cases in exception structure more robustly

- **Made all shared data classes thread-safe** 🔧
  - SMSQueue: Added threading.Lock() to prevent race conditions
  - SMSCounter: Added threading.Lock() for counter operations
  - SMSHistory: Added threading.Lock() for message history access
  - SMSDeliveryTracker: Added threading.Lock() for delivery tracking
  - DeviceConnectivityTracker: Added threading.Lock() for status tracking
  - All public methods now protected with lock
  - Prevents data corruption when accessed from multiple threads

## [2.10.2] - 2025-11-29

### Fixed

- **Critical: sys.exit(1) doesn't work from threads** 🐛
  - Auto-restart was being called but process didn't actually exit
  - SMS monitoring runs in a background thread where sys.exit() only kills the thread
  - Changed to os.\_exit(1) which forcefully terminates the entire process
  - Now addon will actually restart when device errors (Code 2/11) are detected

## [2.10.1] - 2025-11-29

### Fixed

- **Critical: Restart timer was being reset prematurely** 🐛
  - Timer was resetting when reconnect "succeeded" even if modem still broken
  - Now only resets on actual successful Gammu operation
  - Fixes issue where 2-minute restart timeout never triggered

- **Critical: Code 11 (ERR_DEVICEWRITEERROR) not handled** 🐛
  - "Error writing to the device" now triggers immediate restart
  - Same handling as Code 2 (device unavailable)

- **Critical: Queued SMS not sent after modem recovery** 🐛
  - Pending SMS now processed when modem comes back online
  - No longer waits for addon restart to retry queued messages

## [2.10.0] - 2025-11-29

### Added

- **SMS Queue with Persistence** 📥 - Failed SMS are now queued for automatic retry
  - Messages queued to `/data/pending_sms.json` for persistence across restarts
  - Queued messages automatically sent when modem recovers
  - Queue processed on addon startup after modem initialization
  - Messages expire after 1 hour (prevents stale message delivery)
  - Duplicate prevention (same number+text won't be queued twice)

- **Auto-Restart on Persistent Failure** 🔄 - New `auto_restart_on_failure` option
  - Addon automatically restarts after 2 minutes of continuous modem failure
  - Immediate restart on device unavailable error (USB disconnected)
  - Restart handled by HA Supervisor for clean recovery
  - Configurable via `auto_restart_on_failure: true` (default: enabled)
  - Fastest recovery method for hung modems per user testing

- **Extended Error Recovery** - Added ERR_DEVICEOPENERROR (Code 2) detection
  - Detects when USB device becomes unavailable
  - Triggers immediate addon restart for fastest recovery

### Changed

- **SMS Send Failure Handling** - No longer throws errors on send failure
  - Failed messages are queued instead of causing API errors
  - Response includes count of sent and queued messages
  - Other recipients still receive messages if one fails

## [2.9.2] - 2025-11-29

### Fixed

- **Full Modem Reconnect on Errors** 🔧 - Fixed retry using stale modem connection
  - Now performs full Gammu re-initialization when soft reset fails
  - Retry uses the reconnected modem instance (not the old broken one)
  - Soft reset tested first (10s wait), falls back to full reconnect if unresponsive
  - Additional 5s wait after reconnect before SMS retry
  - Fixes issue where retry failed with same ERR_NOTCONNECTED error

## [2.9.1] - 2025-11-29

### Added

- **Comprehensive Modem Error Recovery** 🔄 - Extended hung modem detection to all recoverable errors
  - ERR_TIMEOUT (14): Command timed out
  - ERR_EMPTYSMSC (31): Cannot retrieve SMSC number
  - ERR_NOTCONNECTED (33): Phone not connected
  - ERR_BUG (37): Protocol implementation error
  - ERR_PHONE_INTERNAL (56): Internal phone error
  - ERR_GETTING_SMSC (69): Failed to get SMSC from phone
  - All trigger: emergency reset + 7s wait + automatic retry
  - Reference: <https://docs.gammu.org/c/error.html>

## [2.9.0] - 2025-11-28

### Added

- **ERR_EMPTYSMSC Auto-Recovery** 🔄 - Automatic detection and recovery from modem hung state
  - Detects ERR_EMPTYSMSC (error code 31) when modem cannot retrieve SMSC number
  - Triggers emergency modem soft reset automatically
  - Waits 7 seconds for modem recovery
  - Automatically retries SMS send once after reset
  - Prevents SMS loss when modem enters hung state

- **SMSC Caching** 📞 - Caches SMS Service Center number for reliability
  - Retrieves and caches SMSC number from modem on startup
  - Uses explicit SMSC number instead of location lookup (more reliable)
  - Cache refreshes every hour or after modem reset
  - Falls back to location lookup if caching fails

### Changed

- **SMS Sending** - Now uses cached SMSC for all outgoing messages
  - More reliable than location-based SMSC lookup
  - Reduces dependency on modem state for SMSC retrieval

## [2.8.7] - 2025-11-26

### Fixed

- **Status Sensor Display** 🔧 - Fixed sensors stuck showing "clearing" after restart
  - Removed unnecessary intermediate "clearing" state for status sensors
  - Status sensors now publish final states (ready/idle) directly with retain=True
  - Eliminates race condition that caused sensors to show "clearing" indefinitely
  - All status sensors (send/delete/delivery) immediately show correct values

## [2.8.6] - 2025-11-26

### Fixed

- **JSON Parse Errors** 🐛 - Fixed MQTT JSON errors during status sensor clearing
  - Changed status sensor clearing from None to valid JSON {"status": "clearing"}
  - All status sensors (send/delete/delivery) now receive valid JSON at all times
  - Resolves "Erroneous JSON" and "'value_json' is undefined" errors in HA logs

## [2.8.5] - 2025-11-26

### Fixed

- **Status Display** 🔧 - Fixed delivery_status and USSD code display issues
  - Removed intermediate "initializing" state for delivery_status (now directly publishes "idle")
  - Fixed USSD Code field showing "unknown" by publishing valid placeholder "\*#" instead of empty string
  - Resolves delivery_status stuck on "initializing" during HA restarts
  - USSD Code now properly respects pattern validation (requires USSD format)

## [2.8.4] - 2025-11-26

### Fixed

- **Startup Crash** 🐛 - Fixed UnboundLocalError on addon startup
  - Moved `import time` to beginning of \_publish_initial_states method
  - Fixed crash that prevented status sensors from being initialized
  - Status sensors now properly receive their initial states
  - Resolves "Unknown" sensor values that occurred due to initialization failure

## [2.8.3] - 2025-11-26

### Fixed

- **Status Sensor Clearing** 🔧 - Fixed retain flag for delivery_status clearing
  - Changed retain from False to True when publishing clearing message
  - Ensures old retained messages are properly replaced with valid JSON
  - Prevents "Unknown" sensor states after restart
  - Maintains fix for JSON parse errors from v2.8.2

## [2.8.2] - 2025-11-26

### Fixed

- **MQTT JSON Error on Startup** 🐛 - Fixed template errors in Home Assistant logs
  - Fixed "Erroneous JSON" error when clearing retained MQTT messages
  - Fixed "'value_json' is undefined" template error for delivery_status sensor
  - delivery_status topic now cleared with valid JSON instead of null payload
  - Added USSD code field to startup clearing routine to prevent "unknown" values
  - All sensor topics with value_json templates now always receive valid JSON

## [2.8.1] - 2025-11-25

### Fixed

- **Last SMS Sensors Restoration** 🔄 - Fixed blank SMS sensors after restart
  - Last received SMS data is now restored from history on addon startup
  - SMS state messages use MQTT retain to persist across Home Assistant restarts
  - "Last SMS Received" and "Last SMS Sender" sensors populate immediately after restart
  - Fixed timing issue by restoring SMS after discovery configs are processed
  - No need to wait for a new SMS to arrive to see previous message
  - SMS history loaded from persistent storage and republished to MQTT

- **Delivery Tracker Status Sensor** 📬 - Fixed status persistence behavior
  - Delivery status now follows same pattern as other event-driven status sensors
  - Publishes "idle" state on startup (no longer retains "cleared" across restarts)
  - Uses retain=False like send_status and delete_status sensors
  - Event-driven status sensors should show current state, not persist old events
  - Added verification logging after clearing delivery reports

## [2.8.0] - 2025-11-25

### Added

- **SMS Received Count Sensor** 📨 - New counter to track incoming SMS messages
  - Separate counter from SMS Sent Count for better statistics
  - Persistent storage survives addon restarts
  - Automatically increments when SMS messages are received
  - Includes dedicated reset button: "Reset SMS Received Counter"
  - Both counters use `state_class: total_increasing` for proper Home Assistant statistics
  - Enables tracking of SMS volume patterns over time

### Improved

- **Sensor State Classes** 📊 - Enhanced Home Assistant statistics support
  - Added `state_class: "measurement"` to GSM Signal Strength (%) sensor
  - Added `state_class: "measurement"` to SMS Storage Used sensor
  - Added `state_class: "measurement"` to Minutes Remaining balance sensor
  - Added `state_class: "measurement"` to Messages Remaining balance sensor
  - These changes enable long-term statistics, trend analysis, and better automation support
  - Follows Home Assistant best practices for numeric sensors

### Changed

- **Button Names Clarified** 🔘 - Improved naming for better clarity
  - "Reset SMS Counter" renamed to "Reset SMS Sent Counter"
  - Distinguishes between sent and received counter reset buttons

## [2.7.0] - 2025-11-25

### Added

- **MVNO Network Code Handling** 📱 - Improved support for Mobile Virtual Network Operators
  - Handles modem quirk where operator names appear in NetworkCode field (e.g., "Red Pocket")
  - Implements reverse lookup in network database to find numeric codes for MVNO names
  - Network code caching mechanism preserves numeric codes across polling cycles
  - Ensures Network Code sensor shows stable numeric values (e.g., "310260")
  - Network Name sensor correctly displays MVNO brands when broadcast by tower
  - Works for all MVNOs: those with own codes (Assurance Wireless, Xfinity Mobile) and host network users (Red Pocket)
  - Resolves issue where Network Code sensor would intermittently show operator names instead of MCC+MNC codes
- **Clear Delivery Reports Button** 📦 - New control to clear stuck delivery reports
  - Useful when SMS delivery reports don't work properly with certain modems/SIMs
  - Clears all pending delivery reports from tracking database
  - Accessible via Home Assistant device controls or MQTT button
  - Publishes confirmation to delivery_status topic when cleared

### Changed

- **Network Codes Database Update** 📊 - Expanded operator coverage
  - Added 180 new network codes (2,869 → 3,049 total entries)
  - Improved multi-MCC section handling in update script (fixes 310-316 range)
  - All 42 manual MVNO overrides verified and preserved
  - Better coverage for US, Canadian, and international carriers

## [2.6.1] - 2025-11-24

### Fixed

- Fixed SMS monitoring polling logs not appearing in debug mode (condition was checking for 'verbose' instead of 'debug')

## [2.6.0] - 2025-11-24

### Added

- **GSM Network Type Sensor** 📶 - Cellular technology detection with AT command support
  - Displays network technology (2G/3G/4G/5G/NB-IoT/EN-DC) from modem
  - Uses AT+CEREG? and AT+CGREG? commands to retrieve Access Technology (AcT)
  - Automatically detects LTE, UMTS, GSM, 5G NR, and other network types
  - 5-minute caching to minimize modem disconnects and maximize reliability
  - Falls back to "Unknown" if modem doesn't support AcT reporting
  - Full 3GPP TS 27.007 compliance (AcT values 0-13)
  - Tested and working on SIM7600G-H and similar LTE modems

- **Packet Location Area Code Sensor** 📍 - New diagnostic sensor
  - Tracks location area code for packet-switched (data) connections
  - Complements existing LAC sensor (circuit-switched voice)
  - Useful for monitoring data network roaming and handoffs

## [2.5.0] - 2025-11-24

### Added

- **GSM Network Type Sensor** 📶 - New diagnostic sensor for cellular technology detection
  - Displays network technology (2G/3G/4G/5G/NB-IoT/EN-DC)
  - Comprehensive support for all network types including 5G NR and EN-DC
  - Currently shows "Unknown" as Gammu API doesn't expose Access Technology by default
  - Framework in place for future AT command-based detection
  - Full 3GPP TS 27.007 compliance (AcT values 0-13)
  - Documentation added for troubleshooting and technical details

## [2.4.1] - 2025-11-24

### Fixed

- **Auto-Recovery Bug** 🐛 - Critical fix for automatic modem recovery
  - Fixed issue where background threads continued using old broken Gammu connection after recovery
  - All operations now use `self.gammu_machine` instead of function parameter
  - SMS monitoring, status publishing, and initial states now pick up new connection immediately
  - Recovery now actually works instead of appearing successful but continuing to fail
  - Eliminates conflict between auto_recovery and old soft reset mechanisms

- **Sensor Name Disambiguation** - Fixed duplicate sensor name
  - Changed dBm signal sensor name from "GSM Signal Strength" to "GSM Signal Strength (dBm)"
  - Makes it easier to distinguish between percentage and dBm sensors in Home Assistant

## [2.4.0] - 2025-11-24

### Added

- **Automatic Modem Recovery** 🔄 - Recover from modem communication failures without restart
  - New `auto_recovery` option (default: `true`) - configurable automatic recovery
  - Monitors modem communication for consecutive failures
  - Triggers reconnection after 5 consecutive failures
  - 60-second cooldown between reconnection attempts
  - Re-initializes Gammu state machine to restore modem communication
  - Publishes device status (offline → online) when reconnection succeeds
  - **Eliminates need for external automation** to restart addon on modem disconnect
  - Can be disabled by setting `auto_recovery: false` if needed

- **Modem Firmware Sensor** 🔧 - New diagnostic sensor showing modem firmware version
  - Displays modem firmware version at startup and in Home Assistant
  - Marked as diagnostic entity (appears in diagnostics section)
  - Useful for troubleshooting and support
  - Uses chip icon (mdi:chip)

## [2.3.1] - 2025-11-23

### Fixed

- **Syntax Error** 🐛 - Critical fix for startup crash
  - Removed orphaned `except` block in periodic status publisher
  - Fixes Python syntax error preventing add-on from starting
  - Resolves "SyntaxError: invalid syntax" on line 2198

## [2.3.0] - 2025-11-23

### Improved

- **Combined Status Logging** 📊 - Reduced log overflow
  - Single line for status updates: `📡 Status update: 87% (-55 dBm) | T-Mobile/Metro by T-Mobile`
  - INFO level shows signal and network info combined
  - DEBUG level displays detailed sensor breakdowns
  - Significantly reduces log verbosity during periodic updates

### Changed

- **Logging Level Names** ⚠️ BREAKING CHANGE - Now use Python's standard logging levels
  - `warning` instead of `minimal` (Python WARNING level)
  - `info` instead of `normal` (Python INFO level)
  - `debug` instead of `verbose` (Python DEBUG level)
  - Provides consistency with Python logging framework
  - Old values still work but new names are recommended

## [2.2.0] - 2025-11-23

### Added

- **Configurable Status Update Interval** 📊 - Control how often signal and network info updates
  - New `status_update_interval` option (default: 300 seconds / 5 minutes)
  - Range: 30-3600 seconds (30 seconds to 1 hour)
  - Controls update frequency for signal strength, network info, and BER
  - Lower values = more frequent updates, higher values = less modem load
  - Recommended: 60-120s for mobile/weak signal, 300-600s for stationary setups
  - Displays configured interval at startup

- **Configurable Logging Levels** 📋 - Control log verbosity to reduce spam
  - New `log_level` option with three levels: `warning`, `info` (default), `debug`
  - `warning` - Only warnings and errors (Python WARNING level)
  - `info` - All useful info, suppresses repetitive SMS polling "OK" messages (Python INFO level)
  - `debug` - Full debug logging including all polling cycles (Python DEBUG level)
  - Solves log overflow from SMS monitoring cycles (every 5-10 seconds)
  - All important events (SMS received/sent, signal strength, network info) remain visible in info mode
  - Uses Python's standard logging level names for consistency
  - Documented in DOCS.md with clear explanations of each level

### Changed

- **SMS Check Interval** - Reduced minimum from 10 to 5 seconds
  - `sms_check_interval` now accepts 5-300 seconds (previously 10-300)
  - Default changed to 5 seconds for faster SMS detection
  - Allows near-instant SMS notifications for time-sensitive use cases

- **Translation Updates** 🌍 - Complete localization coverage
  - Updated all 10 translation files (cs, de, en, es, fr, it, nl, pl, pt, sk)
  - Added missing configuration items: `status_update_interval`, `log_level`, `sms_history_max_messages`, `sms_delivery_reports`, `balance_sms_enabled`, `balance_sms_sender`, `balance_keywords`
  - Updated `sms_check_interval` range description to reflect new 5-300s range
  - All UI strings now properly localized for better user experience

## [2.1.7] - 2025-11-22

### Added

- **SMS-Based Balance Tracking** 💰 - Parse account balance info from provider SMS
  - Automatically detects and parses balance SMS from configured sender
  - Extracts: account balance, data remaining (MB), minutes remaining, messages remaining, plan expiry date
  - Creates dedicated Home Assistant sensors for each balance metric
  - Configurable via `balance_sms_enabled`, `balance_sms_sender`, and `balance_keywords` options
  - Example: Send "Balance" or "Getinfo" to provider number (e.g., 7039) to receive balance information
  - Persistent storage of balance data in `/data/balance_data.json`
  - Regex-based parsing supports multiple provider message formats

## [2.1.6] - 2025-11-22

### Changed

- **Event Data Field Names** - Updated to match deprecated integration for backwards compatibility
  - Changed `sender` to `phone` to match `legacy_gsm_sms.incoming_sms` event format
  - Kept `text` field name (already compatible)
  - Kept `date` field name (already compatible)
  - Added extra fields: `timestamp` (unix timestamp) and `state` (SMS read state)
  - Old automations using deprecated integration can now work without changes

## [2.1.5] - 2025-11-22

### Fixed

- **Event System API Access** 🔐 - Added required Home Assistant API permission
  - Added `homeassistant_api: true` to config.yaml
  - This grants addon permission to call Home Assistant Core API
  - Fixes HTTP 401 Unauthorized error when firing events
  - Uses supervisor proxy: `http://supervisor/core/api/events/`

## [2.1.4] - 2025-11-22

### Fixed

- **Event System Authentication** 🔐 - Fixed HTTP 401 Unauthorized error
  - Changed to use single quotes for headers
  - Use default empty string for token
  - Split URL construction for better clarity
  - Log token length instead of full token for security

## [2.1.3] - 2025-11-22

### Added

- **Enhanced Event System Logging** 🔍 - Improved visibility for event firing process
  - Clear emoji indicators (🔔 attempting, ✅ success, ❌ error)
  - Detailed debug messages for troubleshooting
  - Better error handling for network and authentication issues
  - Makes it easier to diagnose why events might not be firing

## [2.1.2] - 2025-11-22

### Added

- **Event-Based SMS Notifications** 🆕 - Reliable notification system using Home Assistant events
  - Fires `sms_gateway_message_received` event for every received SMS via Home Assistant REST API
  - Event data includes: phone, text, date, timestamp, state
  - No duplicate notifications after addon restarts (unlike state-based triggers)
  - Use `platform: event` with `event_type: sms_gateway_message_received` in automations
  - Access data via `{{ trigger.event.data.phone }}` and `{{ trigger.event.data.text }}`
  - Uses supervisor token to directly fire events (same method as standalone addon)
  - Example automations included in documentation (filter by sender, filter by keyword)

## [2.1.1] - 2025-11-22

### Added

- **List Support for Multiple Recipients** - REST API now properly accepts phone numbers as JSON array
  - Supports single number string: `"number": "+1234567890"`
  - Supports comma-separated string: `"number": "+123,+456"`
  - Supports JSON array: `"number": ["+123", "+456"]` (recommended for multiple recipients)
  - Supports string representation of lists for compatibility
  - Use `{{ target | tojson }}` in rest_command payload for proper JSON serialization
  - Enables cleaner YAML list format in Home Assistant automations

### Changed

- **Improved JSON Parsing** - Fixed request handling to properly parse JSON arrays
  - Now uses `request.get_json()` first for proper JSON body parsing
  - Falls back to reqparse for query parameters and form data
  - Correctly handles all phone number formats without errors
- Added debug logging for SMS send requests (text, numbers, type)
- Enhanced number parsing with multiple fallback strategies

### Fixed

- Fixed 500 Internal Server Error when sending to multiple recipients via JSON array
- Fixed reqparse not properly handling JSON array payloads

## [2.1.0] - 2025-11-20

### Changed

- **Base Image Update** - Updated to Alpine 3.22 base image
  - Security improvements and CVE patches
  - Performance optimizations
  - Updated Python versions (3.13.x)
  - Modernized tooling (pip 25.2, Bashio 0.17.5)

- **Docker Configuration** - Fixed multi-architecture build support
  - Removed hardcoded architecture from Dockerfile
  - Proper ARG BUILD_FROM usage for multi-arch builds
  - Updated Dockerfile labels with correct version and maintainer

- **Startup Logging & Dependencies** - Enhanced version visibility and fixed dependencies
  - Added version display in startup logs
  - Fixed version loading to read from config.yaml
  - Added PyYAML and requests to dependencies

- **Documentation Corrections** - Fixed incorrect service documentation
  - Removed incorrect `notify.sms_gateway` service (addons cannot create notify services)
  - Added `rest_command` wrapper as alternative for service-like interface
  - Updated all automation examples to use correct methods

### Added

- **USSD Support** - Send USSD codes (e.g., \*#100# for balance check) directly from Home Assistant
  - USSD Code text field - Enter USSD codes (validates format: starts with \*, e.g., \*225#, \*#100#)
  - Send USSD button - Execute USSD code and receive network response
  - USSD Response sensor - Displays network response with timestamp
  - Uses Gammu's DialService for reliable USSD execution
  - Automatic code clearing after successful send
  - Error handling with user-friendly messages

- **SMS History Tracking** - Received messages stored with persistence
  - Messages include phone number, full message text, and timestamp
  - Available as JSON attributes on Last SMS Received sensor
  - Persistent storage survives addon restarts
  - Configurable history length (default: 10 messages, range: 1-100)
  - Automatic trimming keeps only most recent messages
  - Access via `state_attr('sensor.sms_gateway_last_sms', 'history')`

- **SMS Delivery Reports** - Optional delivery status tracking (disabled by default)
  - Enable via `sms_delivery_reports: true` in configuration
  - Automatic delivery report request for sent SMS when enabled
  - Message reference tracking with persistent storage
  - Delivery status sensor shows pending/delivered status
  - Includes message preview, timestamps, and recipient number
  - Note: Some carriers may charge for delivery reports

### Use Cases

- Check mobile account balance (\*#100#, \*#123#, etc.)
- Query remaining data/minutes (\*#111#, \*#150#, etc.)
- Activate/deactivate carrier services
- USSD-based service interactions
- Review recent SMS messages in automations
- Track SMS communication patterns
- Monitor SMS delivery success/failure
- Track message delivery timing for critical notifications

## [2.0.1] - 2025-11-20

### Added

- **Last SMS Sender Sensor** - New dedicated sensor displaying phone number of last received SMS
  - Entity: `sensor.sms_gateway_last_sms_sender`
  - Extracts phone number from incoming SMS data
  - Separate from Last SMS Received sensor (which shows message text)
  - Simplifies automations that need to respond based on sender
  - Uses phone icon (mdi:phone) for easy identification

### Changed

- **Documentation Updates** - Updated README.md and DOCS.md to include new sensor

## [2.0.0] - 2025-11-19

### Added - Enhanced Edition by BigThunderSR

- **Comprehensive Network Provider Lookup Database** - Automatic operator identification using MCC+MNC codes
  - United States carriers: AT&T, Verizon, T-Mobile/Metro by T-Mobile, US Cellular, Sprint, and regional carriers
  - International carriers: Major operators in 100+ countries worldwide
  - Fallback to Gammu's built-in network names when operator not in database
- **Human-Readable Network States** - Network registration status displayed in plain English
  - "Registered (Home)" instead of "HomeNetwork"
  - "Registered (Roaming)" instead of "RoamingNetwork"
  - "Searching" instead of "RequestingNetwork"
  - "Registration Denied" instead of "RegistrationDenied"
  - "Not Registered" instead of "NoNetwork"
- **Enhanced Signal Diagnostics** - Separate sensors for different signal metrics
  - GSM Signal Strength (%) - Main sensor with percentage display
  - GSM Signal Strength (dBm) - Diagnostic sensor showing actual radio signal strength
  - Both sensors update together from same data source
- **Bit Error Rate Monitoring** - Network quality diagnostic sensor
  - GSM Bit Error Rate sensor (0-7% scale)
  - Filters invalid -1 values to show as unavailable
  - Diagnostic category for advanced users
- **Cell Tower Information Sensors** - Location and network area diagnostics
  - GSM Cell ID - Current cell tower identifier
  - GSM Location Area Code - Network area code
  - Both marked as diagnostic sensors
- **Network Code Sensor** - MCC+MNC display for debugging
  - Shows raw network code (e.g., "310-260" for T-Mobile)
  - Helpful for troubleshooting network lookup issues
  - Diagnostic category
- **Enhanced Device Path Logging** - Troubleshooting assistance for by-id paths
  - Logs configured device path on startup
  - Shows by-id symlink resolution with actual device path
  - Displays helpful error messages with solutions when device not accessible
  - Suggests adding resolved device to allowlist if needed
- **Reorganized MQTT Topics** - Better entity grouping in Home Assistant
  - Changed from `homeassistant/sensor/sms_gateway_signal/config` pattern
  - To `homeassistant/sensor/sms_gateway/signal/config` pattern
  - All entities now share consistent node_id for better organization
  - Applies to all sensors, buttons, and text entities
- **Sensor Organization** - Clear distinction between main and diagnostic sensors
  - Main sensors: Signal %, Network name, Network state, SMS-related
  - Diagnostic sensors: Signal dBm, BER, Network code, Cell ID, LAC, Modem info
  - Diagnostic sensors marked with `entity_category: "diagnostic"`

### Changed

- **Network Name Lookup** - Now uses comprehensive database with multiple fallback layers
  - Priority: network_codes.py database → Gammu GSMNetworks → "Unknown"
  - Significantly improved operator identification accuracy
- **MQTT Discovery Structure** - All discovery topics reorganized for consistency
  - Better grouping in MQTT broker view
  - All entities properly linked to single "SMS Gateway" device
- **BER Sensor Display** - Invalid values now handled gracefully
  - -1 (invalid/unavailable) filtered to None
  - Shows as "unavailable" in Home Assistant instead of -1
- **Translation Files** - Fixed SMS check interval range (10-300 seconds) and currency defaults (USD first) in all translation files
- **Version Number** - Bumped to 2.0.0 to reflect major enhancements

### Credits

This enhanced version is based on:

- **PavelVe's SMS Gammu Gateway** (v1.5.3) - <https://github.com/PavelVe/home-assistant-addons>
- **Original pajikos/sms-gammu-gateway** - <https://github.com/pajikos/sms-gammu-gateway>
- Both licensed under Apache License 2.0

All enhancements maintain full compatibility with the Apache License 2.0.

---

## [1.5.3] - 2025-11-06

### Added

- **Extended Device Support** - Added ttyUSB4, ttyUSB5 for multi-port Huawei modems
- **Extended ACM Support** - Added ttyACM1, ttyACM2, ttyACM3 for cdc_acm driver modems

## [1.5.2] - 2025-11-04

### Fixed

- **Modem Communication Freezing** - Fixed hanging AT commands with Gammu commtimeout (10s) and Python-level timeout (15s)
- **Race Condition** - Added threading lock to serialize all Gammu operations and prevent parallel AT command execution
- **Buffer Overflow** - Added 0.3s delay between commands to prevent modem buffer issues (Huawei E1750)

### Enhanced

- **Automatic Recovery** - Modem soft reset after 2 consecutive failures
- **Offline Detection** - Increased timeout from 10 to 15 minutes

## [1.5.1] - 2025-10-29

### Enhanced

- **Improved Modem Status Monitoring** - Enhanced online/offline detection with better error handling and recovery
- **Extended Message Length** - Message Text field now supports up to 255 characters (MQTT text entity limit)
- Gammu automatically splits longer messages into multiple SMS parts during sending. Incoming message is also limited to 255 characters.
- **Persistent Device IDs** - Support for stable `/dev/serial/by-id/` paths that survive modem reconnections
- **Smart Availability** - Entities automatically become unavailable in Home Assistant when addon stops

## [1.5.0] - 2025-10-28

### 🚀 Major Feature Update - SMS Management & Tracking Suite

This release introduces comprehensive SMS management capabilities including automatic Unicode handling, persistent message tracking with cost monitoring, advanced SIM card management, and detailed modem diagnostics.

📱 **What's New in the SMS Gateway Addon**

Based on your feedback, I’ve implemented a bunch of new features! 🚀

- 🔤 Automatic Unicode detection – ensures correct delivery of messages with diacritics
- 📊 Persistent sent SMS counter + optional total cost sensor
- 🔘 Button to reset counters
- 🧹 Auto-delete of read SMS + button to delete all messages
- 🧠 New REST API endpoints for SMS management
- 📡 Extended modem diagnostics (IMEI, model, IMSI, manufacturer)
- 💾 SMS storage capacity sensor
- 🌍 Added new translations – now available in **10 languages**

💬 Update now and explore all the new features!

### Added

#### SMS Sending Enhancements (MQTT/REST)

- **Automatic Unicode Detection** - When sending SMS via MQTT, the addon now automatically detects whether the message contains non-ASCII characters (such as diacritics like háčky and čárky). When detected, Unicode mode is automatically enabled, ensuring proper delivery of messages with special characters.
- MQTT method intelligently switches encoding based on message content
- REST API remains unchanged with explicit `unicode` parameter control for backward compatibility

#### SMS Counter & Cost Tracking

- **Persistent SMS Sent Counter** - New sensor `sms_gateway_sent_count` tracks total number of SMS messages sent through the addon (via both MQTT and REST API)
- Counter state persists across addon restarts using JSON file storage at `/data/sms_counter.json`
- Counter increments automatically on every successful SMS send operation
- **Optional Cost Tracking Sensor** - New configuration option `sms_cost_per_message` (default: 0.0) enables SMS cost monitoring
- When set to non-zero value, creates `sms_gateway_total_cost` sensor displaying cumulative cost of all sent messages
- **Configurable Currency** - New `sms_cost_currency` configuration field for customizing cost display (EUR, USD, CZK, etc.)
- **Reset Counter Button** - New MQTT button `sms_gateway_reset_counter` for easy one-click reset of SMS counter and total costs back to zero

#### SIM Card SMS Management

- **Automatic SMS Deletion** - New configuration option `auto_delete_read_sms` (default: false) automatically deletes SMS messages from SIM card after they are read during monitoring cycle
- Helps prevent SIM card storage exhaustion on cards with limited SMS capacity
- **Delete All SMS Button** - New MQTT button `sms_gateway_delete_all_sms` for bulk deletion of all SMS messages stored on SIM card
- **New REST Endpoint** - Added `DELETE /sms/deleteall` endpoint for programmatic deletion of all SMS messages via REST API
- **Automatic Capacity Refresh** - SMS storage capacity sensor automatically updates after both manual deletion (via button) and automatic deletion operations

#### Modem Diagnostics & Information

- **Enhanced Modem Information Sensors** - New diagnostic sensors providing detailed hardware information:
  - **Modem IMEI** - International Mobile Equipment Identity number
  - **Modem Manufacturer** - Device manufacturer name
  - **Modem Model** - Specific device model identification
  - **SIM IMSI** - International Mobile Subscriber Identity from inserted SIM card
- **SMS Storage Capacity Sensor** - New sensor `sms_gateway_sms_storage_used` displaying number of SMS messages currently stored on SIM card
- Includes full capacity details in sensor attributes (SIMUsed, SIMSize, PhoneUsed, PhoneSize, TemplatesUsed)
- Displayed unit: "messages" with icon `mdi:email-multiple`
- **New REST Endpoints** for modem information:
  - `GET /status/modem` - Retrieve modem hardware information (IMEI, manufacturer, model, firmware version)
  - `GET /status/sim` - Get SIM card information (IMSI number)
  - `GET /status/sms_capacity` - Query SMS storage capacity and current usage statistics

### Enhanced

- **Counter Integration** - Both MQTT and REST API methods increment the SMS counter automatically on successful message transmission
- **MQTT Discovery** - Extended Home Assistant MQTT discovery with all new sensors and buttons for seamless integration
- **Persistent Storage** - SMS counter and cost data survives addon restarts and updates

### Configuration

- `sms_cost_per_message` (float, default: 0.0) - Price per SMS message for cost tracking (set to 0 to disable cost sensor)
- `sms_cost_currency` (string, default: "CZK") - Currency code for cost display (EUR, USD, CZK, GBP, etc.)
- `auto_delete_read_sms` (bool, default: false) - Enable automatic deletion of SMS after reading during monitoring

### Extended Device Support

- Added `/dev/ttyUSB2`, `/dev/ttyUSB3`, and `/dev/ttyS0` to supported device paths for broader
  hardware compatibility

### Technical Details

- Added `detect_unicode_needed()` function using ASCII encoding check to determine if Unicode mode is required
- Created `SMSCounter` class with JSON-based persistent storage mechanism
- MQTT Unicode handling: uses explicit `unicode` parameter if provided, otherwise performs automatic detection
- SMS counter data published to `{topic_prefix}/sms_counter/state` as JSON: `{"count": N, "cost": X.XX}`
- Modem information published on addon startup and available via REST API endpoints
- Auto-delete functionality integrated into SMS monitoring loop when enabled
- SMS storage capacity automatically refreshed after deletion operations to reflect current state

## [1.3.2] - 2025-08-21

### Changed

- **Sensor Naming Improvement** - Renamed "USB Device Status" to "Modem Status" for better clarity
- Updated sensor icon from `mdi:usb` to `mdi:connection` for more appropriate representation
- Improved logging messages with better emoji indicators (📶 ONLINE, ❌ OFFLINE)
- Updated unique_id from `sms_gateway_device_status` to `sms_gateway_modem_status`

## [1.3.1] - 2025-08-21

### Added

- **USB Device Status Sensor** - New MQTT sensor monitoring GSM device connectivity
- Real-time tracking of device communication success/failure
- Detailed device status with attributes: last_seen, consecutive_failures, last_error
- Smart offline detection (10 minutes without successful communication)
- Status logging with emoji indicators (📱 ONLINE, 🚫 OFFLINE, ❓ UNKNOWN)

### Enhanced

- **Comprehensive Gammu Operation Tracking** - All gammu communications now monitored
- REST API endpoints, periodic status checks, SMS operations tracked
- Automatic device status updates on every communication attempt
- Home Assistant auto-discovery includes new USB Device Status sensor

### Technical Details

- Added `DeviceConnectivityTracker` class for communication monitoring
- Wrapped all gammu operations with connectivity tracking
- Device status published to MQTT topic: `{topic_prefix}/device_status/state`
- Status states: "online", "offline", "unknown" with detailed attributes

## [1.3.0] - 2025-08-21

### Fixed

- **MQTT Unicode Support** - Fixed MQTT SMS sending to properly handle Unicode messages
- MQTT method now respects `"unicode": true` parameter in JSON payload (was previously ignored)
- Unicode messages sent via MQTT now display correctly instead of showing ????

### Technical Details

- Updated `mqtt_publisher.py` to extract and use unicode parameter from MQTT JSON payload
- Modified `_send_sms_via_gammu()` method to accept unicode_mode parameter
- Fixed hard-coded `"Unicode": False` that prevented Unicode encoding in MQTT messages
- MQTT Unicode handling now matches REST API and Native HA Service behavior

## [1.2.9] - 2025-08-19

### Fixed

- **Signal Strength Sensor** - Removed invalid `device_class: "signal_strength"` to make sensor appear in Home Assistant
- **MQTT Discovery** - Signal strength sensor now properly discovered and displayed in HA

### Technical Details

- Signal strength sensor uses percentage (%) instead of dBm, so device_class was incompatible
- Removed device_class allows HA to treat it as generic sensor with % unit

## [1.2.8] - 2025-08-19

### Changed

- Renamed add-on directory from `GamuGatewaySMS` to `sms-gammu-gateway` for consistency

## [1.2.6] - 2025-08-19

### Changed

- **Smart Field Clearing** - Only message text clears after sending, phone number persists for convenience
- Phone number stays for sending multiple messages to same recipient

## [1.2.5] - 2025-08-19

### Fixed

- **REST API Notify Compatibility** - API now accepts both standard and Home Assistant notify parameters
- Supports `text`/`message` and `number`/`target` interchangeably for better compatibility

## [1.2.4] - 2025-08-19

### Fixed

- **UI/Backend Sync** - Text fields now properly synchronize between Home Assistant UI and backend state
- Enhanced MQTT synchronization with bidirectional state handling

## [1.2.3] - 2025-08-19

### Fixed

- **Text Field Clearing** - Both phone number and message fields now clear reliably after sending
- Enhanced field validation and UI synchronization

### Removed

- SMSC Number configuration field (no longer needed)

## [1.2.1] - 2025-08-19

### Added

- **SMSC Configuration** - New optional "SMSC Number" field in addon configuration
- Smart SMSC priority: configured SMSC → SIM SMSC → fallback

## [1.2.0] - 2025-08-19

### Fixed

- **Gammu Error Code 69** - Better handling of SMSC number issues with automatic detection
- Both text fields now clear after SMS send for consistency

### Changed

- **Breaking Change**: Both text fields now clear after SMS send (was keeping phone number)

## [1.1.9] - 2025-08-19

### Fixed

- **Empty Fields on Startup** - Text fields now start empty instead of showing "unknown"
- **Smart Field Clearing** - Only message text clears after send, phone number stays
- **Better Error Messages** - User-friendly SMS error messages instead of raw gammu codes

## [1.1.8] - 2025-08-19

### Added

- **Text Input Fields** - Phone Number and Message Text fields directly in SMS Gateway device
- **Smart Button Functionality** - Send SMS button now uses values from text input fields
- **Auto-clear Fields** - Text fields automatically clear after successful SMS send
- **Field Validation** - Shows error if trying to send without filling required fields

## [1.1.7] - 2025-08-19

### Added

- **SMS Send Button** - New button entity in Home Assistant device for easy SMS sending
- **SMS Send Status Sensor** - Shows status of SMS sending operations
- **Home Assistant Service** - Native `send_sms` service with phone number and message fields

## [1.1.5] - 2025-08-19

### Added

- **MQTT SMS Sending** - Send SMS messages via MQTT topic subscription
- **Command Topic** - Subscribe to MQTT commands for SMS sending
- **JSON Command Format** - Simple JSON payload: `{"number": "+420123456789", "text": "Hello!"}`

## [1.1.4] - 2025-08-19

### Added

- **Simple Status Page** - New user-friendly HTML page for Home Assistant Ingress
- **External Swagger Link** - Button to open full API documentation

## [1.1.0] - 2025-08-19

### Added

- **SMS Monitoring Toggle** - Configuration option to enable/disable automatic SMS detection
- **Configurable Check Interval** - Adjust SMS monitoring frequency (30-300 seconds)
- **Enhanced SMS Storage** - SMS messages stored in HA database with full history

## [1.0.9] - 2025-08-19

### Added

- **Automatic SMS Detection** - Background monitoring for incoming SMS messages
- **Real-time SMS Notifications** - New SMS automatically published to MQTT

## [1.0.8] - 2025-08-19

### Added

- **Initial MQTT State Publishing** - Publish sensor states immediately on startup
- **Retained MQTT Messages** - Values persist across Home Assistant restarts

## [1.0.5] - 2025-08-19

### Added

- **MQTT Bridge** - Optional MQTT integration with Home Assistant auto-discovery
- **3 Automatic Sensors** - GSM Signal Strength, Network Info, Last SMS Received
- **Periodic Status Updates** - Every 5 minutes to MQTT
- **Real-time SMS Notifications** - Instant MQTT publish on SMS receipt

## [1.0.4] - 2025-08-19

### Added

- **Swagger UI Documentation** - Professional API documentation at `/docs/`
- Interactive API testing interface with organized endpoints

## [1.0.0] - 2025-08-19

### Added

- Initial release of SMS Gammu Gateway Home Assistant Add-on
- REST API for sending and receiving SMS messages
- Support for USB GSM modems with AT commands
- Basic authentication for SMS endpoints
- Multi-architecture support (amd64, i386, aarch64, armv7, armhf)

### Features

- Send SMS via POST /sms
- Retrieve all SMS via GET /sms
- Get specific SMS by ID via GET /sms/{id}
- Delete SMS by ID via DELETE /sms/{id}
- Check signal quality via GET /signal
- Get network information via GET /network
- Reset modem via GET /reset
- HTTP Basic Authentication for protected endpoints
