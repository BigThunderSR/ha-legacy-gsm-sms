# GSM SMS Gateway Enhanced

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]

Enhanced SMS Gateway with comprehensive network diagnostics and operator identification

> **⚠️ Important Compatibility Note:**  
> Do not run this add-on simultaneously with the HACS Legacy GSM SMS integration or any other GSM addon - they will conflict when accessing the modem's serial device. Stop/uninstall any existing GSM integrations before starting this add-on.

## About

This add-on provides an enhanced SMS gateway solution for Home Assistant with advanced network monitoring capabilities. It offers both REST API and MQTT interfaces for sending and receiving SMS messages through USB GSM modems, plus detailed network diagnostics.

**Why use this add-on?** The official Home Assistant SMS integration was removed in 2025.12. While the [HACS integration](../README.md#hacs-integration) currently works (via pre-built wheels), it's not officially supported and may break in the future. This add-on includes Gammu and is guaranteed to work on all Home Assistant installation types.

**Credits and Attribution:**

- **Based on:** [PavelVe's SMS Gammu Gateway](https://github.com/PavelVe/home-assistant-addons/tree/main/sms-gammu-gateway) (Apache License 2.0)
- **Original project:** [pajikos/sms-gammu-gateway](https://github.com/pajikos/sms-gammu-gateway) (Apache License 2.0)
- **Enhanced by:** BigThunderSR with network provider lookup and comprehensive diagnostics

## 🌟 Enhanced Features

### 🆕 What's New in This Version

- **Network Provider Lookup** - Comprehensive MCC+MNC database for automatic operator identification (AT&T, Verizon, T-Mobile, international carriers)
- **Human-Readable Network States** - "Registered (Home)" instead of cryptic "HomeNetwork"
- **Enhanced Signal Diagnostics** - Separate sensors for signal percentage and dBm
- **Bit Error Rate Monitoring** - Network quality diagnostics
- **Cell Tower Information** - Cell ID and Location Area Code sensors
- **Network Code Display** - MCC+MNC code for debugging
- **Organized MQTT Topics** - Better grouping in Home Assistant
- **Enhanced Device Path Logging** - Troubleshooting tips for by-id device paths

### 📱 SMS & USSD Management

- **Send SMS** via REST API, MQTT, or Home Assistant UI
- **Flash SMS Support** ⚡ (🆕 v2.14.0) - Send urgent alerts that display on screen without saving
- **Multiple Recipients** - Send to comma-separated numbers in single request
- **Receive SMS** with automatic MQTT notifications
- **SMS History** - Configurable message history with timestamps (default: 10, up to 100)
- **Delivery Reports** - Optional delivery status tracking (disabled by default, some carriers charge)
- **Send USSD Codes** - Check balance, query data/minutes, activate services
- **USSD Response Display** - View network responses in sensor
- **Balance SMS Tracking** 💰 (🆕 v2.1.7) - Automatic parsing of balance SMS from providers
  - Extracts: account balance, data remaining, minutes, messages, plan expiry
  - Creates dedicated sensors for each metric
  - Example: Send "Balance" or "Getinfo" to provider number to update sensors
  - Supports multiple message formats from different providers
- **Text Input Fields** directly in Home Assistant device
- **Smart Buttons** for easy SMS/USSD sending from UI
- **Phone Number Persistence** - keeps number for multiple messages
- **Automatic Unicode Detection** - special characters handled automatically
- **Delete All SMS Button** - Clear SIM card storage with one click
- **Auto-delete SMS** - Optional automatic deletion after reading
- **Reset Counter Buttons** - Reset SMS sent/received statistics
- **Message Length Limit** - 255 characters max (longer messages split automatically by modem)

### 📊 Device Monitoring

**Main Sensors:**

- **GSM Signal Strength** - Signal percentage (0-100%)
- **GSM Network** - Carrier/operator name with automatic lookup
- **GSM Network State** - Registration status (Registered (Home), Registered (Roaming), etc.)
- **Last SMS Received** - Full message details
- **Last SMS Sender** - Phone number of last received SMS
- **SMS Send Status** - Success/error tracking
- **SMS Sent Count** - Persistent counter (survives restarts)
- **SMS Received Count** - Persistent counter for received messages
- **SMS Storage Used** - SIM card capacity monitoring
- **Modem Status** - Device connectivity tracking

**Diagnostic Sensors:**

- **GSM Signal Strength (dBm)** - Actual signal strength in dBm
- **GSM Bit Error Rate** - Network quality metric (0-7%)
- **GSM Network Code** - MCC+MNC code for debugging
- **GSM Network Type** - Network technology (2G/3G/4G/5G/NB-IoT/EN-DC) 🆕
- **GSM Cell ID** - Current cell tower identifier
- **GSM Location Area Code** - Network area code
- **Modem IMEI** - Device identifier
- **Modem Model** - Manufacturer and model info
- **Modem Firmware** - Modem firmware version (🆕 v2.4.0)
- **SIM IMSI** - SIM card identifier

**Optional:**

- **SMS Total Cost** - Cost tracking (configurable price per SMS)

### 🔧 Integration Options

- **REST API** with Swagger documentation at `/docs/`
- **MQTT Integration** with Home Assistant auto-discovery
- **Native HA Service** `send_sms` for automations
- **Notify Platform** support for alerts
- **Web UI** accessible through Ingress

## Prerequisites

- USB GSM modem supporting AT commands (SIM800L, Huawei E1750, etc.)
- Modem must appear as `/dev/ttyUSB*`, `/dev/ttyACM*`, or `/dev/ttyS*` device
- SIM card with SMS capability
- MQTT broker (core-mosquitto addon recommended)

## Installation

### From GitHub Repository

1. Add this repository to your Home Assistant:

   ```text
   https://github.com/BigThunderSR/ha-legacy-gsm-sms
   ```

2. Find **GSM SMS Gateway Enhanced** in add-on store
3. Click Install
4. Configure the add-on (see below)
5. Start the add-on

### Manual Installation

1. Copy the `addon-gsm-gateway` folder to `/addons/` in your Home Assistant
2. Restart Home Assistant
3. Go to Settings → Add-ons → Add-on Store
4. Refresh and find **GSM SMS Gateway Enhanced**

## Configuration

### Basic Settings

| Option        | Default        | Description                          |
| ------------- | -------------- | ------------------------------------ |
| `device_path` | `/dev/ttyUSB0` | Path to your GSM modem device        |
| `pin`         | `""`           | SIM card PIN (leave empty if no PIN) |
| `port`        | `5000`         | API port                             |
| `ssl`         | `false`        | Enable HTTPS                         |
| `username`    | `admin`        | API username                         |
| `password`    | `password`     | **Change this!** API password        |

### MQTT Settings

| Option              | Default                            | Description                 |
| ------------------- | ---------------------------------- | --------------------------- |
| `mqtt_enabled`      | `true`                             | Enable MQTT integration     |
| `mqtt_host`         | `core-mosquitto`                   | MQTT broker hostname        |
| `mqtt_port`         | `1883`                             | MQTT broker port            |
| `mqtt_username`     | `""`                               | MQTT username (if required) |
| `mqtt_password`     | `""`                               | MQTT password (if required) |
| `mqtt_topic_prefix` | `homeassistant/sensor/sms_gateway` | MQTT topic prefix           |

### SMS Settings

| Option                     | Default | Description                                             |
| -------------------------- | ------- | ------------------------------------------------------- |
| `sms_monitoring_enabled`   | `true`  | Enable SMS monitoring                                   |
| `sms_check_interval`       | `10`    | Check for new SMS every X seconds                       |
| `auto_delete_read_sms`     | `true`  | Auto-delete SMS after reading                           |
| `sms_history_max_messages` | `10`    | Number of SMS to keep in history (1-100)                |
| `sms_delivery_reports`     | `false` | Enable SMS delivery reports (may incur carrier charges) |
| `sms_cost_per_message`     | `0.0`   | Cost per SMS (0 = disabled)                             |
| `sms_cost_currency`        | `USD`   | Currency for cost tracking                              |

### Device Path Options

You can specify the modem path in two ways:

#### Option 1: By device name (simple, but may change)

```yaml
device_path: /dev/ttyUSB0
```

⚠️ **Warning:** This path can change if you disconnect/reconnect the modem or add other USB devices.

#### Option 2: By device ID (recommended, stable)

```yaml
device_path: /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
```

✅ **Recommended:** This path is unique and persistent across reboots and reconnections.

To find your modem's stable ID, run in Home Assistant terminal:

```bash
ls -la /dev/serial/by-id/
```

### Example Configuration

```yaml
device_path: /dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
pin: ""
port: 5000
ssl: false
username: admin
password: "MySecurePassword123!"
mqtt_enabled: true
mqtt_host: core-mosquitto
mqtt_port: 1883
mqtt_username: ""
mqtt_password: ""
mqtt_topic_prefix: homeassistant/sensor/sms_gateway
sms_monitoring_enabled: true
sms_check_interval: 10
sms_cost_per_message: 0.0
sms_cost_currency: USD
auto_delete_read_sms: true
sms_history_max_messages: 10
sms_delivery_reports: false
```

## Usage

### Sending SMS from Home Assistant UI

1. Open Home Assistant
2. Go to Settings → Devices & Services → MQTT
3. Find the **SMS Gateway** device
4. Enter phone number in **Phone Number** field (e.g., `+12345678900`)
5. Enter message in **Message Text** field
6. Click **Send SMS** button (or **Send Flash SMS** for urgent alerts)

> **💡 Tip:** Use comma-separated numbers to send to multiple recipients at once (e.g., `+12345678900,+10987654321`)

### Sending Flash SMS ⚡ (v2.14.0)

Flash SMS (Class 0) messages display immediately on the recipient's screen without being saved to their inbox. Perfect for urgent alerts!

**From Home Assistant UI:**

1. Enter phone number and message as above
2. Click **Send Flash SMS** button instead of regular Send

**Via Automation:**

```yaml
service: button.press
target:
  entity_id: button.sms_gateway_send_flash_button
```

### Sending SMS via Automation

```yaml
service: button.press
target:
  entity_id: button.sms_gateway_send_button
data:
  phone_number: "+12345678900"
  message: "Hello from Home Assistant!"
```

### Sending USSD Codes

USSD codes (like \*#100# for balance) can be sent to query your mobile carrier:

**From Home Assistant UI:**

1. Go to Settings → Devices & Services → MQTT → SMS Gateway device
2. Enter USSD code in **USSD Code** field (e.g., `*#100#`)
3. Click **Send USSD** button
4. View response in **USSD Response** sensor

**Common USSD Codes:**

- `*#100#` - Check account balance (many carriers)
- `*#123#` - Check balance (alternative)
- `*#111#` - Check data usage
- `*#150#` - Check minutes remaining
- Codes vary by carrier - check your mobile provider's documentation

**Via Automation:**

```yaml
# Set USSD code
service: text.set_value
target:
  entity_id: text.sms_gateway_ussd_code
data:
  value: "*#100#"

# Send USSD
service: button.press
target:
  entity_id: button.sms_gateway_send_ussd_button
```

### Monitoring Network Status

All sensors appear under the **SMS Gateway** device:

- Check signal strength: `sensor.gsm_signal_strength`
- Check operator: `sensor.gsm_network`
- Check network state: `sensor.gsm_network_state`
- Check last SMS: `sensor.gsm_last_sms_received`
- Check SMS sender: `sensor.gsm_last_sms_sender`
- Check USSD response: `sensor.sms_gateway_ussd_response`
- Check signal dBm: `sensor.gsm_signal_strength_2` (diagnostic)
- Check BER: `sensor.gsm_bit_error_rate` (diagnostic)
- Check Cell ID: `sensor.gsm_cell_id` (diagnostic)

### REST API

The REST API is available at `http://homeassistant.local:5000` (or your configured port).

**Swagger Documentation:** `http://homeassistant.local:5000/docs/`

**Send SMS:**

```bash
curl -X POST "http://homeassistant.local:5000/send_sms" \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+12345678900", "message": "Hello"}'
```

**Send Flash SMS:** ⚡

```bash
curl -X POST "http://homeassistant.local:5000/send_sms" \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+12345678900", "message": "URGENT!", "flash": true}'
```

**Send to Multiple Recipients:**

```bash
curl -X POST "http://homeassistant.local:5000/send_sms" \
  -u admin:password \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+12345678900,+10987654321", "message": "Hello everyone!"}'
```

**Get Signal Status:**

```bash
curl "http://homeassistant.local:5000/signal" -u admin:password
```

**Get Network Status:**

```bash
curl "http://homeassistant.local:5000/network" -u admin:password
```

## Troubleshooting

### Modem Not Detected

1. Check device path:

   ```bash
   ls -la /dev/ttyUSB*
   ls -la /dev/serial/by-id/
   ```

2. Check addon logs for device path diagnostics:

   ```text
   📱 Configured device path: /dev/serial/by-id/usb-xxxxx
   🔗 By-ID symlink resolves to: /dev/ttyUSB6
   ✅ Resolved device /dev/ttyUSB6 is accessible
   ```

3. If you see "ERROR: Resolved device is NOT accessible":
   - The by-id symlink points to a device not in the addon's allowlist
   - Check the log for the actual device path (e.g., `/dev/ttyUSB6`)
   - The addon already includes `/dev/ttyUSB0-9`, so this shouldn't happen
   - Report as a bug if it does

### Network Name Shows "Unknown"

The addon includes a comprehensive network operator database (MCC+MNC codes). If your carrier shows as "Unknown":

1. Check the **GSM Network Code** sensor to see your MCC+MNC
2. Report the missing code as an enhancement request

### Duplicate Sensors in Home Assistant

If you see duplicate sensors after upgrading:

1. Go to Settings → Devices & Services → MQTT
2. Find the old **SMS Gateway** device entries
3. Delete the old/duplicate entities
4. Restart the addon to republish clean discovery configs

### Signal Strength Always 0%

- Check that the modem has a SIM card installed
- Verify the SIM card PIN (if required)
- Check antenna connection
- View **GSM Signal Strength (dBm)** diagnostic sensor for raw signal value

### Modem Shows Offline When SMS Operations Fail

The **Modem Status** sensor tracks device connectivity. When SMS operations (like retrieving messages) time out, the modem is marked as "offline" with a `hard_offline` state. This prevents false "online" readings when only signal polling succeeds but SMS functionality is broken.

**Status Attributes:**

- `status`: "online" or "offline"
- `hard_offline`: `true` if a timeout caused the offline state (won't clear from signal polling alone)
- `hard_offline_operation`: Which operation timed out (e.g., "retrieveAllSms")
- `consecutive_failures`: Number of failed operations
- `last_error`: Description of the last error

**Recovery:**

The modem will automatically return to "online" when an SMS operation succeeds. If the modem stays offline:

1. Check the addon logs for timeout errors
2. Verify the USB connection is stable
3. Try restarting the addon
4. Check if the SIM card needs to be reseated

### Network Type Shows "Unknown"

The **GSM Network Type** sensor displays the cellular network technology (2G/3G/4G/5G) your modem is connected to. If it shows "Unknown":

**Current Limitations:**

- Gammu's `GetNetworkInfo()` API does not expose Access Technology (AcT) information by default
- Direct AT command access (`AT+CREG?`) would be needed for accurate detection but requires low-level serial communication
- Actual network type detection is not yet implemented

**Technical Details:**

The network type is normally provided by the `AT+CREG?` command's AcT parameter (3GPP TS 27.007):

- 0 = GSM (2G)
- 1 = GSM Compact (2G)
- 2 = UTRAN (3G)
- 3 = GSM w/EGPRS (EDGE/2.5G)
- 4 = UTRAN w/HSDPA (3G+/HSPA)
- 5 = UTRAN w/HSUPA (3G+/HSPA+)
- 6 = UTRAN w/HSDPA and HSUPA (3G+/HSPA+)
- 7 = E-UTRAN (LTE/4G)
- 8 = EC-GSM-IoT (2G IoT)
- 9 = E-UTRAN NB-S1 (NB-IoT)
- 10 = E-UTRA connected to 5GCN (LTE anchored to 5G core)
- 11 = NR connected to 5GCN (5G NR - New Radio)
- 12 = NG-RAN (5G)
- 13 = E-UTRA-NR dual connectivity (EN-DC - simultaneous 4G+5G)

## Network Provider Database

This enhanced version includes a comprehensive database of network operators worldwide:

**United States:**

- AT&T, Verizon, T-Mobile/Metro by T-Mobile, US Cellular, Sprint, and many regional carriers

**International:**

- Major carriers in Canada, UK, Germany, France, Spain, Italy, and 100+ other countries
- Worldwide roaming partners

The database is continuously maintained and can be updated with new carriers.

## Support

For issues, feature requests, or contributions:

- **This enhanced version:** [BigThunderSR/ha-legacy-gsm-sms](https://github.com/BigThunderSR/ha-legacy-gsm-sms/issues)
- **Original PavelVe version:** [PavelVe/home-assistant-addons](https://github.com/PavelVe/home-assistant-addons/issues)

## License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.

This project maintains the Apache License 2.0 from the original works:

- [PavelVe's SMS Gammu Gateway](https://github.com/PavelVe/home-assistant-addons)
- [pajikos/sms-gammu-gateway](https://github.com/pajikos/sms-gammu-gateway)

## Changelog

### Version 2.5.0 (2025-11-24)

**Network Type Detection** 📶 🆕

- New **GSM Network Type** sensor showing cellular technology (2G/3G/4G/5G)
- Comprehensive support for all network types including 5G NR, NB-IoT, and EN-DC
- Lays groundwork for future AT command-based network type detection
- Currently shows "Unknown" as Gammu API doesn't expose Access Technology by default
- Framework in place for modem-specific AT command implementation
- Full 3GPP TS 27.007 compliance (AcT values 0-13)
- Documentation added for troubleshooting and future enhancement

### Version 2.4.1 (2025-11-24)

**Critical Bugfixes** 🐛

- Fixed auto-recovery not actually working (threads continued using old broken connection)
- All Gammu operations now use `self.gammu_machine` to pick up new connection after recovery
- Fixed duplicate sensor name: dBm sensor now named "GSM Signal Strength (dBm)"

### Version 2.4.0 (2025-11-24)

**Automatic Modem Recovery** 🔄

- New `auto_recovery` option (default: `true`) - configurable automatic recovery
- Monitors modem communication for consecutive failures
- Triggers reconnection after 5 consecutive failures
- 60-second cooldown between reconnection attempts
- Re-initializes Gammu state machine to restore modem communication
- Publishes device status (offline → online) when reconnection succeeds
- **Eliminates need for external automation** to restart addon on modem disconnect
- Can be disabled by setting `auto_recovery: false` if needed

**Modem Firmware Sensor** 🔧

- New diagnostic sensor showing modem firmware version
- Useful for troubleshooting and support

### Version 2.1.2 (2025-11-22)

**Event-Based SMS Notifications** 🆕

- New reliable notification system using Home Assistant events
- Fires `sms_gateway_message_received` event for every received SMS via REST API
- No duplicate notifications after addon restarts (unlike state-based triggers)
- Event data includes: sender, text, timestamp, date, state
- Use `platform: event` with `event_type: sms_gateway_message_received` in automations
- Access data via `{{ trigger.event.data.phone }}` and `{{ trigger.event.data.text }}`
- Uses supervisor token to directly fire events (same reliable method as standalone addon)
- Example automations: filter by sender, filter by keyword

### Version 2.1.1 (2025-11-22)

**API Enhancements - Multiple Recipients Support:**

- Fixed REST API to properly handle phone numbers as JSON array
- Improved request parsing using `request.get_json()` for correct JSON array handling
- Now supports four formats:
  - Single number string: `"number": "+1234567890"`
  - Comma-separated string: `"number": "+123,+456"`
  - JSON array: `"number": ["+123", "+456"]` (recommended)
  - String representation of lists (for compatibility)
- Use `{{ target | tojson }}` in rest_command payload for proper JSON serialization
- Enables cleaner YAML list syntax in Home Assistant automations

**Bug Fixes:**

- Fixed 500 Internal Server Error when sending to multiple recipients via JSON array
- Fixed reqparse not properly handling JSON array payloads

**Example:**

```yaml
rest_command:
  send_sms:
    payload: '{"target": {{ target | tojson }}, "text": {{ message | tojson }}}'

# Then use with list:
service: rest_command.send_sms
data:
  target:
    - "+12345678901"
    - "+12345678902"
  message: "Broadcast message"
```

### Version 2.1.0 (2025-11-20)

**Infrastructure Updates:**

- Updated to Alpine 3.22 base image (from 3.19) with security patches and performance improvements
- Fixed Docker multi-architecture build configuration
- Enhanced startup logging with version display banner
- Updated Python to 3.13.x, pip to 25.2, Bashio to 0.17.5

**Features:**

- Added USSD support - send codes like \*#100# to check balance, query data/minutes
- Added USSD Code text field with format validation (supports formats like \*225#, \*#100#, \*611)
- Added Send USSD button and USSD Response sensor
- Automatic code clearing after successful USSD send
- Added SMS history tracking with configurable length (1-100 messages, default: 10)
- SMS history available as JSON attributes on Last SMS sensor
- Added optional SMS delivery reports (disabled by default to avoid carrier charges)

### Version 2.0.1 (2025-11-20)

- Added Last SMS Sender sensor for easier access to incoming phone numbers
- Updated documentation

### Version 2.0.0 (2025-11-19)

- Initial release of enhanced version
- Added comprehensive network provider lookup database (MCC+MNC codes)
- Added human-readable network states (Registered (Home), Registered (Roaming), etc.)
- Added signal strength in dBm (diagnostic sensor)
- Added Bit Error Rate sensor (network quality diagnostic)
- Added Cell ID sensor (cell tower identification)
- Added Location Area Code sensor (network area)
- Added Network Code sensor (MCC+MNC display for debugging)
- Improved BER display (filter -1 invalid values to unavailable)
- Fixed SMS check interval range and currency defaults in all translation files
- Enhanced device path logging with troubleshooting tips
- Reorganized MQTT topics for better grouping
- Fixed sensor naming to avoid duplicates
- Organized sensors into main and diagnostic categories

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
