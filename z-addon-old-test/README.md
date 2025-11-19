# Home Assistant Add-on: Legacy GSM SMS (Old/Test - DEPRECATED)

## ⚠️ DEPRECATED - DO NOT USE

This is the old gammu-based version kept for reference and testing purposes only.

**Please use the [Legacy GSM SMS (Standalone)](../addon-standalone/) add-on instead.**

This version has known issues and is no longer maintained.

---

## About (Historical)

This add-on allows you to:

- Send SMS messages via service call
- Receive SMS messages and fire events
- Monitor modem signal strength
- Monitor network status
- Access GSM network information sensors

## Installation

1. Add this repository to your Home Assistant instance as a custom repository:
   [![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBigThunderSR%2Fha-legacy-gsm-sms)

2. Install the "Legacy GSM SMS" add-on.

## Configuration

### Add-on Configuration

```yaml
device: /dev/ttyUSB0
baud_speed: 0
unicode: false
scan_interval: 30
service_name: legacy_gsm_sms
```

#### Options

- **device** (required): The path to your GSM modem device (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`, etc.)
- **baud_speed** (required): The baud rate for the modem. Use `0` for auto-detection.
- **unicode** (optional): Set to `true` to enable unicode support for SMS messages. Default: `false`.
- **scan_interval** (optional): The interval in seconds to scan for new messages and update sensors. Default: `30`.
- **service_name** (optional): The name of the service to create in Home Assistant. Default: `legacy_gsm_sms`.

## How to use

After installing and starting the add-on:

1. The addon will automatically create the necessary services and sensors.

2. Send an SMS:

   ```yaml
   service: notify.legacy_gsm_sms
   data:
     message: "Hello from Home Assistant!"
     target: "+1234567890"
   ```

3. When an SMS is received, an event will be fired:

   ```yaml
   legacy_gsm_sms.incoming_sms
   ```

4. You can use this event in your automations:

   ```yaml
   trigger:
     platform: event
     event_type: legacy_gsm_sms.incoming_sms
   action:
     service: persistent_notification.create
     data:
       message: "SMS from {{ trigger.event.data.phone }}: {{ trigger.event.data.text }}"
       title: "SMS Received"
   ```

5. The addon also provides these sensors:
   - `sensor.legacy_gsm_sms_signal_strength`: Signal strength as percentage
   - `sensor.legacy_gsm_sms_network_name`: Network name

## Troubleshooting

### Modem not detected

- Ensure your modem is properly connected
- Check if the modem is accessible at the configured device path
- Try different baud rates
- Check the add-on logs for more information

### Permission issues

- The add-on needs access to the device. Make sure you have enabled the required permissions.

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/BigThunderSR/ha-legacy-gsm-sms/issues).
