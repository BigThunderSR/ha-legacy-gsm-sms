# Legacy GSM SMS Add-on

Send and receive SMS messages using a GSM modem with Home Assistant.

## Features

- Send SMS messages via Home Assistant events
- Monitor GSM signal strength
- SMS reception (in development)
- Support for various GSM modems via serial interface

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

Fire an event from Home Assistant:

```yaml
service: event.fire
data:
  event_type: legacy_gsm_sms_send
  event_data:
    number: "+1234567890"
    message: "Hello from Home Assistant!"
```

### Example Automation

```yaml
automation:
  - alias: "Send SMS on Motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion_detector
        to: "on"
    action:
      - service: event.fire
        data:
          event_type: legacy_gsm_sms_send
          event_data:
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

All sensors are grouped under a single device "GSM Modem" with device info (manufacturer, model, firmware).

## Supported Modems

Tested with:

- SimTech SIM7600 series
- Huawei modems
- Most AT-command compatible GSM/3G/4G modems

## Troubleshooting

**Modem not found**: Check device path with `ls -l /dev/ttyUSB*` or `ls -l /dev/serial/by-id/`

**No signal**: Ensure SIM card is inserted and activated

**SMS not sending**: Check addon logs for errors. Verify modem has network connection.
