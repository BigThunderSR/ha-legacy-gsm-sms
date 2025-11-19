# ![brand_icon](png/logo-64x64.png) Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1]

### Fixed

- Fixed sensor values not displaying correctly by properly transforming Gammu data
- Added RSSI to dBm conversion for SignalStrength sensor (matches addon behavior)
- Added RSSI to percentage conversion for SignalPercent sensor
- Improved BitErrorRate sensor to handle unknown values (99) correctly
- Added network state mapping to match addon format (e.g., "Registered (Home)")
- Ensured all 8 sensor entities return proper values with correct units

## [1.0.0]

### Added

- Initial release
- Support for sending and receiving SMS messages via Gammu
- 8 sensor entities: Signal Strength, Signal Percent, Bit Error Rate, Network Name, State, Network Code, CID, LAC
- Home Assistant config flow UI integration
- Event firing for incoming SMS messages
- Notify service for sending SMS
- Compatibility with various GSM modems through Gammu library
