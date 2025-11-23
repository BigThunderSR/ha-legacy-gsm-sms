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
