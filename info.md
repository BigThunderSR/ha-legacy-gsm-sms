# ![brand_icon](png/logo-64x64.png) Legacy GSM SMS

This integration allows you to send and receive SMS messages using a GSM modem connected to your Home Assistant instance.

## Features

- Send SMS messages via notify service
- Receive SMS messages and fire events
- Monitor modem signal strength and network status
- GSM network information sensors

## Installation

1. Install via HACS
2. Restart Home Assistant
3. Go to Configuration > Integrations
4. Add "Legacy GSM SMS" integration
5. Configure the device path to your GSM modem

## Requirements

- A GSM modem connected to your Home Assistant system
- SIM card with SMS capabilities
- Proper permissions to access the modem device

## Configuration

After installation, add the integration through the UI or manually in your `configuration.yaml`:

```yaml
legacy_gsm_sms:
  device: /dev/ttyUSB0  # Update with your modem's device path
```

## Usage

### Send SMS

```yaml
service: notify.legacy_gsm_sms
data:
  message: "Hello from Home Assistant!"
  target:
    - "+1234567890"
```

### Receive SMS

When an SMS is received, an event `legacy_gsm_sms.incoming_legacy_gsm_sms` is fired.
