# How to Send SMS from Home Assistant

The addon listens for events and provides multiple ways to send SMS messages.

## Method 1: Fire Event (Recommended)

Use Home Assistant's `event.fire` service to send SMS:

```yaml
service: event.fire
data:
  event_type: legacy_gsm_sms_send
  event_data:
    number: "+1234567890"
    message: "Hello from Home Assistant!"
```

## Method 2: Command Line (Fallback)

If the event method doesn't work, use the command line queue:

### Step 1: Add shell command to `configuration.yaml`:

```yaml
shell_command:
  send_sms: 'docker exec addon_local_legacy_gsm_sms python3 /usr/bin/send_sms.py --number "{{ number }}" --message "{{ message }}"'
```

### Step 2: Call it from automations:

```yaml
service: shell_command.send_sms
data:
  number: "+1234567890"
  message: "Test message from HA"
```

## Events

The addon fires events back to Home Assistant:

- `legacy_gsm_sms_received` - When SMS is received (currently disabled due to modem issues)
- `legacy_gsm_sms_sent` - When SMS is successfully sent
- `legacy_gsm_sms_failed` - When SMS sending fails

## Example Automation

```yaml
automation:
  - alias: "Send SMS on Motion"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion_detector
        to: "on"
    action:
      - service: event.fire
        data:
          event_type: legacy_gsm_sms_send
          event_data:
            number: "+1234567890"
            message: "Motion detected at {{ now().strftime('%H:%M') }}"
```

## Sensors

The addon creates a sensor `sensor.gsm_modem_status` with:

- State: `connected` or `disconnected`
- Attributes: `signal_strength`, `last_check`, etc.

## Troubleshooting

1. **401 API Errors**: These don't affect SMS functionality, they only affect sensor updates. The addon will still send/receive SMS.

2. **Modem not found**: Check that your device path is correct in the addon configuration. Use `/dev/serial/by-id/...` for stable device names.

3. **SMS not sending**: Check addon logs for errors. Make sure the modem is connected and has signal.

4. **Can't receive SMS**: Currently disabled due to modem stability issues. Will be re-enabled with +CMTI notifications in future version.
