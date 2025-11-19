# Changelog

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
