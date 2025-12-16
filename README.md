# ![brand_icon](png/logo-128x128.png) Legacy GSM SMS for Home Assistant

[![GitHub Release](https://img.shields.io/github/v/release/BigThunderSR/ha-legacy-gsm-sms?label=GitHub%20Release&cacheSeconds=0)](https://github.com/BigThunderSR/ha-legacy-gsm-sms/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?label=HACS)](https://github.com/hacs/integration)
[![HACS Version](https://img.shields.io/github/manifest-json/v/BigThunderSR/ha-legacy-gsm-sms?filename=custom_components%2Flegacy_gsm_sms%2Fmanifest.json&label=HACS%20Version&color=blue&cacheSeconds=0)](https://github.com/BigThunderSR/ha-legacy-gsm-sms)
[![Home Assistant Add-on Version](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2FBigThunderSR%2Fha-legacy-gsm-sms%2Fmain%2Faddon-standalone%2Fconfig.yaml&query=%24.version&label=Home%20Assistant%20Add-on%20Version&color=blue&cacheSeconds=0)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBigThunderSR%2Fha-legacy-gsm-sms)
[![GSM Gateway Enhanced Version](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2FBigThunderSR%2Fha-legacy-gsm-sms%2Fmain%2Faddon-gsm-gateway%2Fconfig.yaml&query=%24.version&label=GSM%20Gateway%20Enhanced&color=green&cacheSeconds=0)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBigThunderSR%2Fha-legacy-gsm-sms)

Send and receive SMS messages using a GSM modem connected to your Home Assistant instance, with sensors for monitoring signal strength and network status.

> **ℹ️ HACS Integration Status:**  
> The official Home Assistant SMS integration was removed in 2025.12. However, this custom HACS integration **currently works** because Home Assistant's wheel index (`wheels.home-assistant.io`) provides pre-built `python-gammu` packages with all Gammu libraries bundled.
>
> **⚠️ Note:** Since this relies on Home Assistant continuing to host these wheels (which are no longer used by any official integration), this could change in the future. If you want a guaranteed long-term solution, consider using one of the [add-on options](#home-assistant-add-ons) instead.

## Features

- Send and receive SMS messages
- Monitor GSM modem signal strength
- Monitor GSM network status
- GSM network information sensors
- Available as HACS integration or Home Assistant add-on

## Requirements

- A GSM modem with AT command support (tested with SimTech SIM7600 series)
- SIM card with SMS capabilities

## Installation

Multiple installation methods are available:

- **[HACS Integration](#hacs-integration)** - Currently working, but not officially supported by HA
- **[Home Assistant Add-ons](#home-assistant-add-ons)** (two options available - guaranteed long-term support):
  - **[Legacy GSM SMS](#legacy-gsm-sms-add-on)** - Standard add-on with HTTP API
  - **[GSM SMS Gateway Enhanced](#gsm-sms-gateway-enhanced-add-on)** - Enhanced add-on with network diagnostics and MQTT support

## Home Assistant Add-ons

Two add-on options are available, each with different features and capabilities. Choose the one that best fits your needs.

### Legacy GSM SMS Add-on

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBigThunderSR%2Fha-legacy-gsm-sms)

The standard add-on provides an HTTP API-based solution for SMS messaging:

**Features:**

- HTTP API for sending SMS messages
- Basic sensor entities for signal strength
- Event-based SMS reception
- Simple configuration and setup

**Installation:**

1. Click the button above to add this repository to your Home Assistant instance
2. Install the "Legacy GSM SMS" add-on from the Add-on Store
3. Configure and start the add-on (refer to the Documentation tab)

### GSM SMS Gateway Enhanced Add-on

**Version 2.1.0** - Enhanced add-on with advanced features and diagnostics.

**Credits:** Based on [PavelVe's SMS Gammu Gateway](https://github.com/PavelVe/hassio-addons) and [pajikos's gammu-sms-gateway](https://github.com/pajikos/gammu-sms-gateway), enhanced with additional diagnostic capabilities.

**Enhanced Features:**

- **MQTT Discovery** - Automatic sensor creation in Home Assistant
- **USSD Support** - Send USSD codes (\*#100# for balance, \*#111# for data usage, etc.)
- **SMS History** - Configurable message history with timestamps (default: 10, up to 100)
- **Delivery Reports** - Optional SMS delivery status tracking (disabled by default)
- **Network Provider Lookup** - Identifies carrier name from MCC/MNC codes
- **Human-readable States** - Modem states translated to plain language
- **Enhanced Diagnostics:**
  - Signal strength (percentage and dBm)
  - Battery status and voltage
  - Network registration state
  - Bit Error Rate (BER)
  - Network operator information
  - Last SMS sender phone number
- **Organized Entity Grouping** - All sensors grouped under single device in HA
- **HTTP API** - Compatible with existing SMS gateway integrations
- **Event-based SMS Reception** - Same as standard add-on

**Installation:**

1. Add this repository to Home Assistant (use button above)
2. Install "GSM SMS Gateway Enhanced" from the Add-on Store
3. Configure your modem device and MQTT settings
4. Start the add-on

Refer to [addon-gsm-gateway/README.md](addon-gsm-gateway/README.md) for detailed documentation, configuration options, and troubleshooting.

**⚠️ Important:** Do not run multiple add-ons or the HACS integration simultaneously - they will conflict when accessing the GSM modem's serial device. Choose only one installation method.

### HACS Integration

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=BigThunderSR&repository=ha-legacy-gsm-sms&category=integration)

> **Note:** This integration works because Home Assistant's wheel index provides pre-built `python-gammu` packages with bundled libraries. Since the official SMS integration was removed, these wheels may not be maintained indefinitely. If you experience issues after a Home Assistant update, switch to one of the [add-on options](#home-assistant-add-ons).

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

1. Go to Settings > Devices & Services > Integrations
2. Click the "+" button to add a new integration
3. Search for "Legacy GSM SMS"
4. Enter the device path to your GSM modem (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`, etc.)
5. Select the baud rate (leave as "Auto" if unsure)

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

Or using the new `legacy_gsm_sms.send_sms` service:

```yaml
service: legacy_gsm_sms.send_sms
data:
  number: "+1234567890"
  message: "Hello from Home Assistant!"
  unicode: true # Optional, defaults to true
  flash: false # Optional, send as Flash SMS (Class 0)
```

#### Sending to Multiple Recipients

You can send to multiple phone numbers by separating them with commas:

```yaml
service: legacy_gsm_sms.send_sms
data:
  number: "+1234567890, +0987654321"
  message: "Hello everyone!"
```

#### Flash SMS (Class 0)

Flash SMS messages display directly on the recipient's screen without being saved to their inbox. Note that support varies by device - modern smartphones may not honor this setting.

```yaml
service: legacy_gsm_sms.send_sms
data:
  number: "+1234567890"
  message: "Urgent alert!"
  flash: true
```

### Sending SMS via UI

The HACS integration now includes text input entities and buttons for sending SMS directly from the Home Assistant UI:

1. Set the phone number in the "Phone Number" text input entity (supports multiple comma-separated numbers)
2. Set the message in the "Message Text" text input entity
3. Press the "Send SMS" button (or "Send Flash SMS" for Class 0 messages)

The text fields will automatically clear after sending.

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

### New Sensors and Entities (v2.0.0)

The HACS integration now includes several new entities matching the addon capabilities:

**Sensors:**

- **SMS Sent Count** - Total number of SMS sent (persisted across restarts)
- **SMS Received Count** - Total number of SMS received (persisted across restarts)
- **Last SMS Received** - Shows the last received SMS with attributes for sender and timestamp
- **Modem Status** - Shows whether the modem is online/offline

**Buttons:**

- **Send SMS** - Sends an SMS using the phone number and message text inputs
- **Send Flash SMS** - Sends a Flash SMS (Class 0) that displays on screen without saving
- **Delete All SMS** - Deletes all SMS from the SIM card
- **Reset Sent Counter** - Resets the sent SMS counter to zero
- **Reset Received Counter** - Resets the received SMS counter to zero

**Text Inputs:**

- **Phone Number** - Enter the recipient phone number for SMS
- **Message Text** - Enter the SMS message content

### Services

The integration provides the following services:

- `legacy_gsm_sms.send_sms` - Send an SMS message (supports multiple recipients and Flash SMS)
- `legacy_gsm_sms.delete_all_sms` - Delete all SMS from SIM
- `legacy_gsm_sms.reset_sent_counter` - Reset sent counter
- `legacy_gsm_sms.reset_received_counter` - Reset received counter

### Configuration Options

After installation, you can configure the integration via Settings > Devices & Services > Legacy GSM SMS > Configure:

- **SMS Check Interval** - How often to check for new SMS (5-300 seconds, default: 10)
- **Auto-delete read SMS** - Automatically delete SMS after reading (default: enabled)
- **Maximum SMS History** - Number of SMS to keep in history (1-100, default: 10)

## Troubleshooting (HACS Integration)

### "Cannot find device" Error

The integration logs `ConfigEntryNotReady` when it cannot connect to the GSM modem:

- Verify the device path is correct (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0`)
- Check available serial devices: `ls -l /dev/ttyUSB* /dev/ttyACM*`
- Ensure the GSM modem is powered on and properly connected
- Check Home Assistant logs for `gammu.GSMError` messages with specific error details

### "Error communicating with device"

This occurs when the GSM modem stops responding after initial connection:

- Check signal strength sensor - poor signal can cause communication failures
- Try a different baud rate (or set to "Auto" for auto-detection)
- Restart Home Assistant to reinitialize the connection
- Ensure no other application is accessing the GSM modem simultaneously

### SMS Not Received

- Check that your SIM card has active service
- Disable SIM PIN if enabled (some GSM modems can't handle PIN-protected SIMs)
- Check the signal strength sensor - weak signal affects SMS reception
- Review logs for `ERR_EMPTY` or `ERR_MEMORY_NOT_AVAILABLE` messages

### Permission Issues (Home Assistant Container/Core)

- Add your user to the `dialout` group: `sudo usermod -a -G dialout $USER`
- Log out and back in for group changes to take effect
- For Home Assistant OS/Supervised, permissions are handled automatically

## Credits

This project is based on the official Home Assistant SMS integration using python-gammu.
