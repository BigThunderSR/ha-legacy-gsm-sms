# ![brand_icon](png/logo-128x128.png) Legacy GSM SMS for Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/BigThunderSR/ha-legacy-gsm-sms)](https://github.com/BigThunderSR/ha-legacy-gsm-sms/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![HACS Version](https://img.shields.io/github/manifest-json/v/BigThunderSR/ha-legacy-gsm-sms?filename=custom_components%2Flegacy_gsm_sms%2Fmanifest.json&label=HACS%20version&color=blue)](https://github.com/BigThunderSR/ha-legacy-gsm-sms)
[![Home Assistant Add-on Version](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2FBigThunderSR%2Fha-legacy-gsm-sms%2Fmain%2Faddon-standalone%2Fconfig.yaml&query=%24.version&label=Add-on%20version&color=blue)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBigThunderSR%2Fha-legacy-gsm-sms)

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

### HACS Integration

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=BigThunderSR&repository=ha-legacy-gsm-sms&category=integration)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations > 3-dot menu > Custom repositories
   - Add the URL of this repository
   - Category: Integration
3. Click "Install" and restart Home Assistant
4. Configure the integration through the UI (see Configuration section below)

#### Manual Installation

Alternatively, you can manually install the integration:

1. Copy the `custom_components/legacy_gsm_sms` folder from this repository into your Home Assistant's `config/custom_components/` directory.
2. Restart Home Assistant.
3. Configure the integration through the UI (see Configuration section below)

## Configuration (HACS Integration)

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

## Usage (HACS Integration)

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

## Home Assistant Add-on (Alternative)

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBigThunderSR%2Fha-legacy-gsm-sms)

As an alternative to the HACS integration, you can install the add-on version:

1. Add this repository to your Home Assistant instance using the button above
2. Install the "Legacy GSM SMS" add-on from the add-on store
3. Follow the configuration and usage instructions in the add-on's Documentation tab

The add-on provides an HTTP API for sending SMS and automatically creates sensor entities for signal strength and network information.

**Note:** Do not run both the HACS integration and the add-on simultaneously, as they will conflict when accessing the serial device.

## Troubleshooting

- Ensure your modem is properly connected and recognized by the system
- Check that your user has permissions to access the device (e.g., add your user to the 'dialout' group)
- Look for errors in the Home Assistant logs

## Credits

This integration is based on the official Home Assistant SMS integration using python-gammu.
