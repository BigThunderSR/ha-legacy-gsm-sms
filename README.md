# ![brand_icon](png/logo-128x128.png) Legacy GSM SMS for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/BigThunderSR/ha-legacy-gsm-sms/releases)
[![Home Assistant Addon](https://img.shields.io/badge/Home%20Assistant-Add--on-blue.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBigThunderSR%2Fha-legacy-gsm-sms)

This integration allows you to send SMS messages using a GSM modem connected to your Home Assistant instance. It also provides sensors for monitoring signal strength and network status.

## Features

- Send SMS messages via service call
- Receive SMS messages and fire events
- Monitor modem signal strength
- Monitor network status
- GSM network information sensors

## Requirements

- A supported GSM modem (tested with Huawei and SIM800/SIM900 based modems)
- Python-gammu package (automatically installed as a dependency)
- SIM card with SMS capabilities

## Installation

### As a Home Assistant Addon (Recommended for Home Assistant OS)

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBigThunderSR%2Fha-legacy-gsm-sms)

1. Add this repository to your Home Assistant instance as a custom repository using the button above
2. Install the "Legacy GSM SMS" add-on from the add-on store
3. Configure the add-on with your modem settings:
   - **device**: Serial device path (e.g., `/dev/ttyUSB0`)
   - **baud_speed**: Connection speed (0 = auto-detect, or specific baud rate)
   - **scan_interval**: How often to poll modem status in seconds (10-600)
   - **log_level**: Logging verbosity (debug, info, warning, error)
4. Start the add-on
5. The addon automatically creates:
   - HTTP API endpoint for sending SMS (port 8099)
   - 8 sensor entities for signal strength and network information
   - Event notifications for incoming SMS messages

### HACS (Alternative for Home Assistant Core/Container)

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=BigThunderSR&repository=ha-legacy-gsm-sms&category=integration)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations > 3-dot menu > Custom repositories
   - Add the URL of this repository
   - Category: Integration
3. Click "Install" and restart Home Assistant

### Manual Installation

1. Copy the `legacy_gsm_sms` directory to your Home Assistant's `custom_components` directory.
2. Restart Home Assistant.

## Configuration

### Through the UI

1. Go to Configuration > Integrations
2. Click the "+" button to add a new integration
3. Search for "Legacy GSM SMS"
4. Enter the device path to your modem (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`, etc.)
5. Select the baud rate (leave as "Auto" if not sure)

### Using configuration.yaml

```yaml
legacy_gsm_sms:
  device: /dev/ttyUSB0
```

## Using the Integration

### Sending SMS

You can send SMS messages using the `notify.legacy_gsm_sms` service:

```yaml
service: notify.legacy_gsm_sms
data:
  message: "Hello from Home Assistant!"
  target:
    - "+1234567890"
```

### Receiving SMS

When an SMS is received, an event `legacy_gsm_sms.incoming_legacy_gsm_sms` is fired with the following data:

- `phone`: The phone number that sent the SMS
- `date`: Timestamp of the SMS
- `text`: Content of the SMS message

You can use this in automations:

```yaml
trigger:
  platform: event
  event_type: legacy_gsm_sms.incoming_legacy_gsm_sms
action:
  service: persistent_notification.create
  data:
    message: "SMS from {{ trigger.event.data.phone }}: {{ trigger.event.data.text }}"
    title: "SMS Received"
```

## Troubleshooting

- Ensure your modem is properly connected and recognized by the system
- Check that your user has permissions to access the device (e.g., add your user to the 'dialout' group)
- Look for errors in the Home Assistant logs

## Credits

This integration is based on the official Home Assistant SMS integration using python-gammu.
