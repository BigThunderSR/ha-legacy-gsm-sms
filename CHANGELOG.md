# ![brand_icon](png/logo-64x64.png) Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0]

### Added - Feature Parity with Addon

This release brings the HACS integration to feature parity with the addon.

#### New Sensors

- **SMS Sent Count** - Tracks total SMS sent (persisted across restarts)
- **SMS Received Count** - Tracks total SMS received (persisted across restarts)
- **Last SMS Received** - Shows last received SMS with sender and timestamp attributes
- **Modem Status** - Shows online/offline status of the modem

#### New Button Entities

- **Send SMS** - Send SMS using the phone number and message text inputs
- **Delete All SMS** - Delete all SMS from the SIM card
- **Reset Sent Counter** - Reset the sent SMS counter to zero
- **Reset Received Counter** - Reset the received SMS counter to zero

#### New Text Input Entities

- **Phone Number** - Text input for entering recipient phone number
- **Message Text** - Text input for entering SMS message content

#### New Services

- `legacy_gsm_sms.send_sms` - Send SMS with number, message, and optional unicode flag
- `legacy_gsm_sms.delete_all_sms` - Delete all SMS messages from SIM
- `legacy_gsm_sms.reset_sent_counter` - Reset sent SMS counter
- `legacy_gsm_sms.reset_received_counter` - Reset received SMS counter

#### Options Flow Configuration

- **SMS Check Interval** - Configure how often to check for new SMS (5-300 seconds)
- **Auto-delete read SMS** - Toggle automatic deletion after reading
- **Maximum SMS History** - Configure number of SMS to keep in history (1-100)

### Changed

- SMS counters and history are now persisted to JSON files in the Home Assistant config directory
- Added SMS manager for centralized SMS tracking

## [1.1.0]

### Added

- MVNO (Mobile Virtual Network Operator) support with intelligent network code handling
- Reverse lookup to find numeric MCC+MNC codes from operator names
- Network code caching to handle modems that alternate between operator name and numeric code
- Improved network name resolution for empty or missing names

### Fixed

- Fixed handling of modem quirk where NetworkCode field contains operator name instead of numeric MCC+MNC
- Better handling of NITZ operator names in network information

## [1.0.1]

### Fixed

- Added network state mapping to user-friendly format (e.g., "Registered (Home)" instead of "HomeNetwork")
- Improved handling of unknown sensor values (-1, 99) by converting to None

### Added

- Comprehensive network operator database with 200+ carriers worldwide
- Network Name lookup for MCC+MNC codes including US, Canada, Europe, Asia, Latin America, and MVNOs
- Fallback to Gammu's GSMNetworks database when operator not in custom database

## [1.0.0]

### Initial Release

- Initial release
- Support for sending and receiving SMS messages via Gammu
- 8 sensor entities: Signal Strength, Signal Percent, Bit Error Rate, Network Name, State, Network Code, CID, LAC
- Home Assistant config flow UI integration
- Event firing for incoming SMS messages
- Notify service for sending SMS
- Compatibility with various GSM modems through Gammu library
