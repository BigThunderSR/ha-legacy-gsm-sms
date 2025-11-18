# Legacy GSM SMS Test Addon

A minimal, clean implementation of the GSM SMS addon for Home Assistant.

## Features

- Send and receive SMS messages via GSM modem
- Monitor signal strength
- Monitor network information
- Fire events for incoming SMS

## Configuration

```yaml
device: /dev/ttyUSB0
baud_speed: 0
scan_interval: 30
log_level: info
```

### Options

- **device**: Path to your GSM modem (e.g., `/dev/ttyUSB0`)
- **baud_speed**: Baud rate (0 = auto-detect)
- **scan_interval**: How often to check for messages (seconds)
- **log_level**: Logging level (debug, info, warning, error)

## Usage

After starting the addon:

1. **Check logs** to verify the modem is connected
2. **Incoming SMS** will fire `legacy_gsm_sms.incoming_sms` events
3. **Sensors** will be created:
   - `sensor.gsm_signal_strength`
   - `sensor.gsm_network`

## Sending SMS

To send SMS, you'll need to call the notify service (to be implemented).

## Development

This is a test version with minimal complexity for easier debugging.
