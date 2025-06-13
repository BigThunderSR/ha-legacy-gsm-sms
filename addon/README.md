# Home Assistant Add-on: Legacy GSM SMS

Send and receive SMS messages using a GSM modem connected to your Home Assistant instance.

## About

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
```

#### Options

- **device** (required): The path to your GSM modem device (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`, etc.)
- **baud_speed** (required): The baud rate for the modem. Use `0` for auto-detection.
- **unicode** (optional): Set to `true` to enable unicode support for SMS messages. Default: `false`.
- **scan_interval** (optional): The interval in seconds to scan for new messages and update sensors. Default: `30`.

## How to use

After installing and starting the add-on:

1. Add the Legacy GSM SMS integration in Home Assistant:
   - Go to **Configuration** > **Integrations**
   - Add a new integration
   - Search for "Legacy GSM SMS"
   - Follow the setup wizard

2. Send an SMS:

   ```yaml
   service: notify.legacy_gsm_sms
   data:
     message: "Hello from Home Assistant!"
     target: "+1234567890"
   ```

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
