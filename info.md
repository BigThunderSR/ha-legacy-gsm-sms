# ![brand_icon](png/logo-64x64.png) Legacy GSM SMS

> **🚨 HACS Integration — DEPRECATED (Broken since HA 2026.3.0)**
>
> The HACS integration **no longer works** starting with Home Assistant 2026.3.0 / OS 17.1. The pre-built `python-gammu` wheels that Home Assistant previously hosted are no longer available. Please use one of the **Home Assistant add-on** options instead.

This integration allows you to send and receive SMS messages using a GSM modem connected to your Home Assistant instance.

## Recommended: Use the GSM SMS Gateway Enhanced Add-on

Add this repository to Home Assistant as an add-on repository and install one of:

- **GSM SMS Gateway Enhanced** ⭐ — **Recommended.** Enhanced add-on with MQTT discovery, USSD, network diagnostics, and more
- **Legacy GSM SMS** — Simpler add-on with HTTP API

See the [full README](https://github.com/BigThunderSR/ha-legacy-gsm-sms) for details.

## Requirements

- A GSM modem connected to your Home Assistant system
- SIM card with SMS capabilities
- Proper permissions to access the modem device

## Configuration

After installation, add the integration through the UI or manually in your `configuration.yaml`:

```yaml
legacy_gsm_sms:
  device: /dev/ttyUSB0 # Update with your modem's device path
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
