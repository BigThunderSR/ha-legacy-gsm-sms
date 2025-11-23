# Legacy GSM SMS Add-on (Standalone)

Send and receive SMS messages using a GSM modem with Home Assistant.

## ⚠️ Important: HACS Integration Compatibility

**Do NOT run this add-on and the HACS integration at the same time!**

Both the add-on and the HACS integration will try to access the same serial device (GSM modem), causing conflicts and preventing either from working properly.

**Before using this add-on:**

1. Disable or uninstall the Legacy GSM SMS HACS integration if you have it installed
2. Restart Home Assistant
3. Then start this add-on

**Which should you use?**

- **HACS Integration**: Best for simple SMS sending/receiving if you don't need add-on features
- **This Add-on**: Provides more sensors (8 total), device info, and additional features

## Features

- **Send SMS** via HTTP API (REST command)
- **Receive SMS** with real-time notifications and Home Assistant events
- **8 Sensor Entities**:
  - Signal Strength (dBm)
  - Signal Percent (%)
  - Bit Error Rate
  - Network Name
  - Registration State
  - Network Code (MCC+MNC)
  - Cell ID (CID)
  - Location Area Code (LAC)
- **Device Information**: IMEI, manufacturer, model, firmware
- **Wide Modem Compatibility**: Uses standard AT commands (no gammu required)

## Configuration

**device**: Serial device path for your GSM modem (default: `/dev/ttyUSB0`)

- Use `/dev/serial/by-id/...` for stable device names
- Find your device with: `ls -l /dev/serial/by-id/`

**baud_speed**: Baud rate for serial communication (default: `0` = auto)

- Most modems work with auto-detection (0)
- Common values: 9600, 19200, 38400, 57600, 115200

**scan_interval**: How often to check for incoming SMS in seconds (default: `30`)

- Range: 10-600 seconds
- Lower values = faster SMS detection, higher CPU usage

**log_level**: Logging verbosity (default: `info`)

- Options: debug, info, warning, error

## Usage

### Sending SMS

Use the REST command integration. Add to your `configuration.yaml`:

```yaml
rest_command:
  send_sms:
    url: "http://addon_slug_legacy_gsm_sms_standalone:8099/send_sms"
    method: POST
    content_type: "application/json"
    payload: '{"number": "{{ number }}", "message": "{{ message }}"}'
```

Then call the service:

```yaml
service: rest_command.send_sms
data:
  number: "+1234567890"
  message: "Hello from Home Assistant!"
```

### Receiving SMS

Incoming SMS automatically fire events. Listen for them in automations:

```yaml
automation:
  - alias: "SMS Received Notification"
    trigger:
      - platform: event
        event_type: legacy_gsm_sms_received
    action:
      - service: notify.mobile_app
        data:
          title: "SMS from {{ trigger.event.data.phone }}"
          message: "{{ trigger.event.data.message }}"
```

### Example Automation - Send SMS on Motion

```yaml
automation:
  - alias: "Send SMS on Motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion_detector
        to: "on"
    action:
      - service: rest_command.send_sms
        data:
          number: "+1234567890"
          message: "Motion detected!"
```

### Events

The addon fires these events:

- `legacy_gsm_sms_received` - SMS received with phone number and message

### Sensors

Creates 8 sensor entities (all grouped by device using IMEI):

- `sensor.gsm_<imei>_signal_strength` - Signal strength in dBm (-113 to -51)
- `sensor.gsm_<imei>_signal_percent` - Signal strength as percentage (0-100%)
- `sensor.gsm_<imei>_bit_error_rate` - Bit error rate percentage
- `sensor.gsm_<imei>_network_name` - Network operator name
- `sensor.gsm_<imei>_state` - Registration state (Home/Roaming/Searching)
- `sensor.gsm_<imei>_network_code` - MCC+MNC network code
- `sensor.gsm_<imei>_cid` - Cell tower ID
- `sensor.gsm_<imei>_lac` - Location Area Code

All sensors are grouped under a single device "Legacy GSM Modem Add-on" with device info (manufacturer, model, firmware).

Sensor names in UI:

- Legacy GSM Modem Add-on Signal Strength
- Legacy GSM Modem Add-on Signal Percent
- Legacy GSM Modem Add-on Bit Error Rate
- Legacy GSM Modem Add-on Network Name
- Legacy GSM Modem Add-on State
- Legacy GSM Modem Add-on Network Code
- Legacy GSM Modem Add-on CID
- Legacy GSM Modem Add-on LAC

## Supported Modems

Tested with:

- SimTech SIM7600 series
- Huawei modems
- Most AT-command compatible GSM/3G/4G modems

## Troubleshooting

**Modem not found**: Check device path with `ls -l /dev/ttyUSB*` or `ls -l /dev/serial/by-id/`

**No signal**: Ensure SIM card is inserted and activated

**SMS not sending**: Check addon logs for errors. Verify modem has network connection.
