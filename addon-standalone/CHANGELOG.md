# Changelog

## v1.0.0

### Initial Release

### Features

- **SMS Sending** via HTTP API (REST command)
  - POST to `http://addon_hostname:8099/send_sms`
  - Thread-safe queue processing
  
- **SMS Receiving** via +CMTI notifications
  - Real-time SMS notifications
  - Fires `legacy_gsm_sms_received` events to Home Assistant
  - Automatic message deletion after reading

- **8 Sensor Entities** (all grouped under "Legacy GSM Modem Add-on" device):
  - Signal Strength (dBm)
  - Signal Percent (%)
  - Bit Error Rate (RXQUAL 0-7, or "unknown")
  - Network Name (operator)
  - State (registration status: Home/Roaming/Searching)
  - Network Code (MCC+MNC)
  - CID (Cell Tower ID)
  - LAC (Location Area Code)

- **Device Information**:
  - IMEI-based device identification
  - Manufacturer, model, and firmware version
  - All sensors grouped under single device

### Technical Details

- Built with **pyserial** (no gammu dependency)
- Minimal AT commands for maximum modem compatibility
- HTTP API on port 8099 for SMS sending
- Event-based architecture for SMS receiving
- Sensors update every scan_interval (default 30s)

### Requirements

- Home Assistant add-on environment
- GSM modem with AT command support (tested with SimTech SIM7600 series)
- SIM card with SMS capabilities
- Serial device access (uart: true)

### Important Notes

⚠️ **Do not run this add-on and the HACS integration simultaneously!**
Both will attempt to access the same serial device, causing conflicts.
Disable or uninstall the HACS integration before using this add-on.

### Configuration Options

- `device`: Serial device path (auto-detected by default)
- `baud_speed`: Serial baud rate (0 = auto-detect, default: 115200)
- `scan_interval`: Sensor update interval in seconds (default: 30)
- `log_level`: Logging verbosity (debug/info/warning/error, default: info)

---

## Development History

For detailed development history, see previous versions in git history.
This represents a complete rewrite from the gammu-based version with improved
stability, compatibility, and feature set.

## 0.0.3d

- **Fixed BER displaying "99%"** - now shows "unknown" when value is 99 (not detectable)
- Removes % unit when BER is unknown to avoid confusion
- When BER is measurable (0-7), shows actual RXQUAL value with % unit

## 0.0.3c

- **Fixed BER sensor not appearing** - now always created even when value is 99 (unknown)
- Most modems return BER=99 (not detectable), sensor now shows this value
- Added note in sensor attributes explaining BER values
- BER sensor will display "99" when modem doesn't support BER measurement

## 0.0.3b

- Fixed Bit Error Rate calculation to return raw RXQUAL value (0-7)
- Added BER value mapping documentation in code
- BER now matches HACS integration behavior
- Lower BER values are better (0 = best, 7 = worst)

## 0.0.3a

- Improved sensor naming for easier discovery
- Device name changed to "Legacy GSM Modem Add-on"
- All sensors now have "Legacy GSM Modem Add-on" prefix in friendly names
- Makes sensors easy to find in entity search and device pages

## 0.0.3

- **All HACS integration sensors now supported!**
- Added NetworkCode sensor (MCC+MNC)
- Added CID sensor (Cell ID)
- Added LAC sensor (Location Area Code)
- Renamed network_operator to network_name (matches HACS)
- Added AT+CREG=2 for network registration location info
- Added get_network_registration() method
- State sensor now shows registration status (Home/Roaming/Searching)
- All 8 sensors match HACS integration structure:
  - Signal Strength (dBm)
  - Signal Percent (%)
  - Bit Error Rate (%)
  - Network Name (operator)
  - State (registration status)
  - Network Code (MCC+MNC)
  - CID (cell tower ID)
  - LAC (location area)
- Sensors properly grouped by device using IMEI
- Friendly names match HACS integration

## 0.0.2c

- Added unique_id attribute to all sensors for UI management
- Added friendly_name to each sensor for better display
- Fixed device identifiers format (removed leading space)
- Sensors now show proper names in HA UI

## 0.0.2b

- Added multiple sensor entities (signal_strength, signal_percent, bit_error_rate, network_operator, state)
- Each sensor has unique ID based on IMEI
- Proper device_class, unit_of_measurement, and icon attributes
- Sensors update every scan_interval (default 30s)
- Device info linked to all sensors (manufacturer, model, firmware)

## 0.0.2a

- Added device info retrieval (IMEI, manufacturer, model, firmware)
- Device info displayed in logs on startup
- Added signal strength and network info methods

## 0.0.1j

- SMS receiving via +CMTI notifications working
- Events fire to Home Assistant (legacy_gsm_sms_received)
- AT+CMGR reads specific SMS by index
- Auto-delete after reading

## 0.0.1

- Complete rewrite using pyserial instead of gammu
- Proper s6-overlay support with bashio
- Event-based SMS sending (`legacy_gsm_sms_send`)
- Minimal permissions (only `uart: true`)
- Fixed modem stability issues
- SMS reading temporarily disabled (will use +CMTI in future)
