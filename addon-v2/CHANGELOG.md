# Changelog

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
