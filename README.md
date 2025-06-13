# ![brand_icon](png/logo-64x64.png) Legacy GSM SMS for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

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

### HACS (Recommended)

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
