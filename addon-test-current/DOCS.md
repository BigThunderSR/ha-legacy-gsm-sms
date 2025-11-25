# SMS Gammu Gateway - Documentation

## 🚀 Quick Start

### Step 1: Connect GSM Modem

- Connect your USB GSM modem (SIM800L, Huawei, etc.)
- Verify detection: Settings → System → Hardware → Search for "ttyUSB" or "ttyACM"
- Supported device paths: `/dev/ttyUSB0-9`, `/dev/ttyACM0-3`, `/dev/ttyS0-3`, `/dev/serial/by-id/`

### Step 2: Basic Configuration

```yaml
device_path: "/dev/ttyUSB0" # Path to modem
username: "admin" # Change this!
password: "strong_password" # Change this!
```

### Step 3: Enable MQTT (Recommended)

```yaml
mqtt_enabled: true
mqtt_host: "core-mosquitto"
```

### Step 4: Start the Add-on

- Click **START**
- Check the log for successful startup
- New device **SMS Gateway** will appear in HA

## 📱 How to Send SMS

> **Note:** This is an **addon**, not an integration. Addons cannot create `notify.*` services. Use one of the methods below instead.

### Method 1: UI Button (Easiest)

1. Go to **Devices** → **MQTT** → **SMS Gateway**
2. Fill **Phone Number** (e.g., +420123456789)
3. Fill **Message Text**
4. Click **Send SMS**

### Method 2: REST Command (Recommended)

> **Note:** The API accepts both `target`/`number` and `text`/`message` as interchangeable parameter names. We use `target` in examples for consistency with Home Assistant's notify service conventions.

Add to `configuration.yaml`:

```yaml
rest_command:
  send_sms:
    url: "http://localhost:5000/sms"
    method: POST
    content_type: "application/json"
    username: "admin"
    password: "password"
    payload: '{"target": {{ target | tojson }}, "text": {{ message | tojson }}}'
```

Then use in automations:

```yaml
# Single recipient
service: rest_command.send_sms
data:
  target: "+420123456789"
  message: "Your message here"

# Multiple recipients (🆕 v2.1.1)
service: rest_command.send_sms
data:
  target:
    - "+420123456789"
    - "+420987654321"
  message: "Broadcast message"
```

### Method 3: MQTT

```yaml
service: mqtt.publish
data:
  topic: "homeassistant/sensor/sms_gateway/send"
  payload: '{"number": "+420123456789", "text": "Alert!"}'
```

### Method 4: REST API

```bash
curl -X POST http://192.168.1.x:5000/sms \
  -u admin:password \
  -d '{"text": "Test", "number": "+420123456789"}'
```

## 🔧 Configuration

### Basic Settings

| Parameter     | Default        | Description                                                                |
| ------------- | -------------- | -------------------------------------------------------------------------- |
| `device_path` | `/dev/ttyUSB0` | Path to GSM modem (supported: ttyUSB0-9, ttyACM0-3, ttyS0-3, serial/by-id) |
| `pin`         | `""`           | SIM card PIN (empty = no PIN)                                              |
| `port`        | `5000`         | API port                                                                   |
| `username`    | `admin`        | API username                                                               |
| `password`    | `password`     | **⚠️ CHANGE THIS!**                                                        |

### MQTT Settings

| Parameter                | Default          | Description                                                             |
| ------------------------ | ---------------- | ----------------------------------------------------------------------- |
| `mqtt_enabled`           | `true`           | Enable MQTT integration                                                 |
| `mqtt_host`              | `core-mosquitto` | MQTT broker hostname                                                    |
| `mqtt_port`              | `1883`           | MQTT broker port                                                        |
| `mqtt_username`          | `""`             | MQTT username (empty for no auth)                                       |
| `mqtt_password`          | `""`             | MQTT password (empty for no auth)                                       |
| `sms_monitoring_enabled` | `true`           | Detect incoming SMS automatically                                       |
| `sms_check_interval`     | `5`              | SMS check interval (5-300 seconds) (🆕 v2.1.8: min reduced to 5s)       |
| `status_update_interval` | `300`            | Status update interval (30-3600 seconds) - signal & network (🆕 v2.1.8) |

### SMS Management Settings

| Parameter                  | Default | Description                                                         |
| -------------------------- | ------- | ------------------------------------------------------------------- |
| `sms_cost_per_message`     | `0.0`   | Price per SMS (0 = cost tracking disabled)                          |
| `sms_cost_currency`        | `USD`   | Currency code (EUR, USD, CZK, GBP, etc.)                            |
| `auto_delete_read_sms`     | `true`  | Auto-delete SMS after reading (frees SIM space)                     |
| `sms_history_max_messages` | `10`    | Number of SMS to keep in history (1-100) (🆕 v2.1.0)                |
| `sms_delivery_reports`     | `false` | Enable SMS delivery reports - may incur carrier charges (🆕 v2.1.0) |
| `log_level`                | `info`  | Logging level: `warning`, `info`, or `debug` (🆕 v2.1.8)            |
| `auto_recovery`            | `true`  | Automatically recover from modem failures (🆕 v2.4.0)               |

### Logging Levels (🆕 v2.1.8, Enhanced v2.2.1)

The `log_level` setting uses Python's standard logging levels:

- **`warning`** - Only warnings, errors, and critical messages (Python WARNING level)
  - Best for production when everything is working smoothly
  - Suppresses all routine status messages
  - Reduces log file size significantly

- **`info`** (default) - Standard operational logging (Python INFO level)
  - Shows all useful information (SMS received/sent, signal strength, network info, connection changes)
  - **Signal strength logs both sensors**: `📡 Published signal strength to MQTT: 75% (-65 dBm)` _(Enhanced v2.2.1)_
  - **Only suppresses**: Repetitive "SMS monitoring cycle OK" messages when no new SMS arrives
  - Recommended for most users - keeps logs clean without hiding important events

- **`debug`** - Full debug logging (Python DEBUG level)
  - Shows everything including "SMS monitoring cycle OK" messages every 5-10 seconds
  - **Displays all sensor details** for signal and network data _(Enhanced v2.2.1)_:
    - Signal: `Signal details: Percent=75%, dBm=-65, BER=0`
    - Network: `Network details: Code=310260, State=HomeNetwork, LAC=1234, CID=5678`
  - Useful for troubleshooting connection issues or development
  - May generate large log files

### Automatic Modem Recovery (🆕 v2.4.0)

The `auto_recovery` setting enables automatic recovery from modem communication failures:

- **`true`** (default) - Automatically reconnects to modem after connection loss
  - Monitors modem communication for consecutive failures
  - Triggers reconnection after **5 consecutive failures**
  - Waits **60 seconds** between reconnection attempts (cooldown period)
  - Re-initializes Gammu state machine to restore modem communication
  - Publishes device status (offline → online) when reconnection succeeds
  - **Recommended**: Enables addon to recover from modem failures without external restart

- **`false`** - Manual recovery required
  - Addon will not attempt automatic recovery
  - Requires external automation or manual restart to recover
  - Use only if automatic recovery causes issues with your specific modem

**Use Case**: If your GSM modem loses USB connection (power loss, physical disconnect, driver issues), the addon will automatically attempt to recover without requiring a full addon restart or external automation.

### Status Update Interval (🆕 v2.1.8)

The `status_update_interval` setting controls how often the addon queries and publishes:

- Signal strength (percentage and dBm)
- Network information (operator, state, cell tower)
- Bit Error Rate (BER)

**Important Notes:**

- GSM modems don't support event-driven notifications for signal changes
- The addon must actively poll the modem using AT commands
- Default: 300 seconds (5 minutes) - reasonable balance between freshness and modem load
- Range: 30-3600 seconds (30 seconds to 1 hour)
- Lower values = more frequent updates but more modem queries
- Higher values = less modem load but less frequent updates

**Recommendations:**

- **Mobile users / weak signal areas**: 60-120 seconds for more frequent updates
- **Stationary setups with stable signal**: 300-600 seconds (default or higher)
- **Battery-powered modems**: 600-1800 seconds to reduce power consumption

### Balance SMS Tracking Settings (🆕 v2.1.7)

| Parameter             | Default                         | Description                                                       |
| --------------------- | ------------------------------- | ----------------------------------------------------------------- |
| `balance_sms_enabled` | `false`                         | Enable automatic parsing of balance SMS messages                  |
| `balance_sms_sender`  | `7069`                          | Phone number that sends balance information (the response sender) |
| `balance_keywords`    | `["Remaining", "expires", ...]` | Keywords in the response message to detect balance SMS            |

**How it works:**

1. You send "Balance" or "Getinfo" to your provider (e.g., 7039)
2. Provider responds from a different number (e.g., 7069)
3. Addon checks: Is sender = `balance_sms_sender` AND does message contain any `balance_keywords`?
4. If yes → Automatically parse and update balance sensors

**Example response messages that will be detected:**

From 7069 after sending "Balance" to 7039:

- "You have 200.00 MB of High Speed Data **Remaining** 200 Minutes & 934 Messages." (keyword: "Remaining")

From 7069 after sending "Getinfo" to 7039:

- "Your plan **expires** on 2025-12-20. You have **balance of** $3.00" (keywords: "expires", "balance of")

When enabled, the addon will automatically detect SMS messages from `balance_sms_sender` containing any of the `balance_keywords`, parse the data, and create dedicated sensors for:

- Account balance (dollar amount)
- Data remaining (MB/GB converted to MB)
- Minutes remaining
- Messages remaining
- Plan expiry date

### Example Configuration with v2.1.8+ Features

````yaml
device_path: "/dev/ttyUSB0"
pin: ""
username: "admin"
password: "change_this_password"
mqtt_enabled: true
mqtt_host: "core-mosquitto"
sms_monitoring_enabled: true
sms_check_interval: 5 # Check for new SMS every 5 seconds (min: 5s, default: 5s)
status_update_interval: 300 # Update signal/network every 5 minutes (default)
auto_delete_read_sms: true
sms_history_max_messages: 20 # Keep last 20 received SMS (default: 10)\nsms_delivery_reports: false # Keep disabled to avoid carrier charges\nsms_cost_per_message: 0.05\nsms_cost_currency: \"USD\"\nlog_level: \"info\" # warning | info | debug (default: info)\n```
````

## 📊 MQTT Sensors

After enabling MQTT, these entities are automatically created:

### Status Sensors

| Entity                               | Type   | Description                                        |
| ------------------------------------ | ------ | -------------------------------------------------- |
| `sensor.sms_gateway_modem_status`    | Sensor | Modem connectivity status (online/offline)         |
| `sensor.sms_gateway_signal`          | Sensor | GSM signal strength in %                           |
| `sensor.sms_gateway_signal_dbm`      | Sensor | GSM signal strength in dBm (🆕 v2.0.0)             |
| `sensor.sms_gateway_ber`             | Sensor | Bit Error Rate - network quality (🆕 v2.0.0)       |
| `sensor.sms_gateway_network`         | Sensor | Network operator name with provider lookup (🆕)    |
| `sensor.sms_gateway_network_state`   | Sensor | Human-readable network state (🆕 v2.0.0)           |
| `sensor.sms_gateway_network_code`    | Sensor | MCC+MNC network code (🆕 v2.0.0)                   |
| `sensor.sms_gateway_network_type`    | Sensor | Network technology 2G/3G/4G/5G (🆕 v2.5.0)         |
| `sensor.sms_gateway_cid`             | Sensor | Cell tower ID (🆕 v2.0.0)                          |
| `sensor.sms_gateway_lac`             | Sensor | Location Area Code (🆕 v2.0.0)                     |
| `sensor.sms_gateway_last_sms`        | Sensor | Last received SMS with history (🆕 v2.1.0 history) |
| `sensor.sms_gateway_last_sms_sender` | Sensor | Phone number of last SMS sender (🆕 v2.0.1)        |
| `sensor.sms_gateway_send_status`     | Sensor | SMS send operation status                          |
| `sensor.sms_gateway_delete_status`   | Sensor | SMS delete operation status                        |
| `sensor.sms_gateway_delivery_status` | Sensor | SMS delivery report status (🆕 v2.1.0)             |
| `sensor.sms_gateway_ussd_response`   | Sensor | USSD response from network (🆕 v2.1.0)             |

### Modem Information Sensors

| Entity                                | Type   | Description                  |
| ------------------------------------- | ------ | ---------------------------- |
| `sensor.sms_gateway_modem_imei`       | Sensor | Modem IMEI number            |
| `sensor.sms_gateway_modem_model`      | Sensor | Modem manufacturer and model |
| `sensor.sms_gateway_sim_imsi`         | Sensor | SIM card IMSI number         |
| `sensor.sms_gateway_sms_storage_used` | Sensor | Number of SMS on SIM card    |

### SMS Counter & Cost Sensors

| Entity                              | Type   | Description                                            |
| ----------------------------------- | ------ | ------------------------------------------------------ |
| `sensor.sms_gateway_sms_sent_count` | Sensor | Total SMS sent through addon                           |
| `sensor.sms_gateway_total_cost`     | Sensor | Total cost of sent SMS (if `sms_cost_per_message > 0`) |

### Balance Sensors (🆕 v2.1.7)

These sensors are created when `balance_sms_enabled: true`:

| Entity                                  | Type   | Description                                   |
| --------------------------------------- | ------ | --------------------------------------------- |
| `sensor.sms_gateway_account_balance`    | Sensor | Account balance (e.g., "$3.00")               |
| `sensor.sms_gateway_data_remaining`     | Sensor | High-speed data remaining (e.g., "200.00 MB") |
| `sensor.sms_gateway_minutes_remaining`  | Sensor | Voice minutes remaining                       |
| `sensor.sms_gateway_messages_remaining` | Sensor | SMS messages remaining                        |
| `sensor.sms_gateway_plan_expiry`        | Sensor | Plan expiration date (e.g., "2025-12-20")     |

**Usage:**

- Send "Balance" to your provider's number (e.g., 7039) → Gets data/minutes/messages remaining
- Send "Getinfo" to your provider's number (e.g., 7039) → Gets account balance and plan expiry date

The addon automatically detects, parses, and updates the sensors when responses arrive.

### Controls

| Entity                                | Type       | Description                       |
| ------------------------------------- | ---------- | --------------------------------- |
| `text.sms_gateway_phone_number`       | Text input | Phone number input field          |
| `text.sms_gateway_message_text`       | Text input | Message text input field          |
| `text.sms_gateway_ussd_code`          | Text input | USSD code input (🆕 v2.1.0)       |
| `button.sms_gateway_send_button`      | Button     | Send SMS button                   |
| `button.sms_gateway_send_ussd_button` | Button     | Send USSD code button (🆕 v2.1.0) |
| `button.sms_gateway_reset_counter`    | Button     | Reset SMS counter and costs       |
| `button.sms_gateway_delete_all_sms`   | Button     | Delete all SMS from SIM card      |

## 🎯 Automation Examples

### SMS on Door Open

```yaml
automation:
  - alias: "Security - Door Opened"
    trigger:
      platform: state
      entity_id: binary_sensor.front_door
      to: "on"
    action:
      service: rest_command.send_sms
      data:
        target: "+420123456789"
        message: "ALERT: Front door opened!"
```

### SMS on Low Temperature

```yaml
automation:
  - alias: "Freeze Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.outside_temperature
      below: 0
    action:
      service: rest_command.send_sms
      data:
        target: "+420123456789"
        message: "Warning: Freezing temperature! Current: {{ states('sensor.outside_temperature') }}°C"
```

### SMS on Power Failure (UPS)

```yaml
automation:
  - alias: "Power Failure Alert"
    trigger:
      platform: state
      entity_id: sensor.ups_status
      to: "on_battery"
    action:
      service: rest_command.send_sms
      data:
        target: "+420123456789"
        message: "Power failure detected! UPS on battery."
```

### Check Balance with USSD (Daily)

```yaml
automation:
  - alias: "Daily Balance Check"
    trigger:
      platform: time
      at: "09:00:00"
    action:
      - service: text.set_value
        target:
          entity_id: text.sms_gateway_ussd_code
        data:
          value: "*#100#"
      - service: button.press
        target:
          entity_id: button.sms_gateway_send_ussd_button
      - delay:
          seconds: 5
      - service: notify.persistent_notification
        data:
          title: "Mobile Balance"
          message: "{{ states('sensor.sms_gateway_ussd_response') }}"
```

### Notify on Received SMS (Event-Based) 🆕

**Recommended:** Use event triggers for reliable SMS notifications that won't duplicate after addon restarts:

```yaml
automation:
  - alias: "Notify on SMS Received"
    trigger:
      platform: event
      event_type: sms_gateway_message_received
    action:
      - service: notify.persistent_notification
        data:
          title: "SMS from {{ trigger.event.data.phone }}"
          message: "{{ trigger.event.data.text }}"
```

### Filter SMS by Sender

```yaml
automation:
  - alias: "Alert on SMS from Specific Number"
    trigger:
      platform: event
      event_type: sms_gateway_message_received
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.phone == '+420123456789' }}"
    action:
      - service: notify.persistent_notification
        data:
          title: "Important SMS"
          message: "{{ trigger.event.data.text }}"
```

### Filter SMS by Keyword

```yaml
automation:
  - alias: "Alert on Password Reset SMS"
    trigger:
      platform: event
      event_type: sms_gateway_message_received
    condition:
      - condition: template
        value_template: "{{ 'password' in trigger.event.data.text | lower }}"
    action:
      - service: persistent_notification.create
        data:
          title: "Security Alert"
          message: "Password reset SMS received: {{ trigger.event.data.text }}"
```

### Check Data Usage with USSD

```yaml
automation:
  - alias: "Check Data Usage"
    trigger:
      platform: state
      entity_id: input_button.check_data
    action:
      - service: text.set_value
        target:
          entity_id: text.sms_gateway_ussd_code
        data:
          value: "*#111#"
      - service: button.press
        target:
          entity_id: button.sms_gateway_send_ussd_button
```

### Balance Tracking via SMS (🆕 v2.1.7)

```yaml
automation:
  # Automatically check balance weekly (detailed usage info)
  - alias: "Check Balance Weekly"
    trigger:
      platform: time
      at: "08:00:00"
    condition:
      - condition: time
        weekday:
          - mon
    action:
      - service: rest_command.send_sms
        data:
          target: "XXXX" # Your provider's balance query number (e.g., 7039)
          message: "Balance" # Gets data/minutes/messages remaining

  # Check account balance and expiry monthly
  - alias: "Check Account Info Monthly"
    trigger:
      platform: time
      at: "09:00:00"
    condition:
      - condition: template
        value_template: "{{ now().day == 1 }}" # First day of month
    action:
      - service: rest_command.send_sms
        data:
          target: "XXXX" # Your provider's balance query number (e.g., 7039)
          message: "Getinfo" # Gets account balance and plan expiry

  # Alert when data is low
  - alias: "Alert on Low Data"
    trigger:
      platform: numeric_state
      entity_id: sensor.sms_gateway_data_remaining
      below: 50
    action:
      - service: notify.mobile_app
        data:
          title: "Low Data Warning"
          message: "Only {{ states('sensor.sms_gateway_data_remaining') }} remaining!"

  # Alert when plan expires soon
  - alias: "Plan Expiry Reminder"
    trigger:
      platform: time
      at: "09:00:00"
    condition:
      - condition: template
        value_template: >
          {% set expiry = states('sensor.sms_gateway_plan_expiry') %}
          {% if expiry not in ['unknown', 'unavailable', ''] %}
            {% set days_left = (as_timestamp(expiry) - now().timestamp()) / 86400 %}
            {{ days_left <= 7 and days_left > 0 }}
          {% else %}
            false
          {% endif %}
    action:
      - service: persistent_notification.create
        data:
          title: "Plan Expiring Soon"
          message: "Your plan expires on {{ states('sensor.sms_gateway_plan_expiry') }}"
```

### Access SMS History

```yaml
# View last 10 SMS messages in template
template:
  - sensor:
      - name: "SMS History"
        state: "{{ state_attr('sensor.sms_gateway_last_sms', 'history') | length }}"
        attributes:
          messages: "{{ state_attr('sensor.sms_gateway_last_sms', 'history') }}"

# Example: Notify if specific number appears in history
automation:
  - alias: "Check SMS History for Number"
    trigger:
      platform: state
      entity_id: sensor.sms_gateway_last_sms
    condition:
      - condition: template
        value_template: >
          {{ '+1234567890' in state_attr('sensor.sms_gateway_last_sms', 'history') | map(attribute='number') | list }}
    action:
      - service: notify.persistent_notification
        data:
          title: "SMS from Watched Number"
          message: "Received SMS from monitored contact"
```

### Monitor SMS Delivery Status

```yaml
# Alert if SMS delivery fails
automation:
  - alias: "Alert on Failed SMS Delivery"
    trigger:
      platform: state
      entity_id: sensor.sms_gateway_delivery_status
      to: "failed"
    action:
      - service: notify.persistent_notification
        data:
          title: "SMS Delivery Failed"
          message: >
            Failed to deliver SMS to {{ state_attr('sensor.sms_gateway_delivery_status', 'number') }}
            Message: {{ state_attr('sensor.sms_gateway_delivery_status', 'text_preview') }}

# Track pending deliveries
template:
  - sensor:
      - name: "Pending SMS Deliveries"
        state: "{{ state_attr('sensor.sms_gateway_delivery_status', 'pending_count') | int(0) }}"
        unit_of_measurement: "messages"
```

## 📡 REST API

### Swagger Documentation

Full API documentation: `http://your-ha-ip:5000/docs/`

### Main Endpoints

#### SMS Operations

| Method | Endpoint         | Description                  |
| ------ | ---------------- | ---------------------------- |
| POST   | `/sms`           | Send SMS message             |
| GET    | `/sms`           | Get all SMS messages         |
| GET    | `/sms/{id}`      | Get specific SMS by ID       |
| DELETE | `/sms/{id}`      | Delete specific SMS          |
| DELETE | `/sms/deleteall` | Delete all SMS from SIM card |

#### Status & Information

| Method | Endpoint               | Description                                     |
| ------ | ---------------------- | ----------------------------------------------- |
| GET    | `/status/signal`       | GSM signal strength                             |
| GET    | `/status/network`      | Network operator info                           |
| GET    | `/status/modem`        | Modem hardware info (IMEI, model, manufacturer) |
| GET    | `/status/sim`          | SIM card information (IMSI)                     |
| GET    | `/status/sms_capacity` | SMS storage capacity and usage                  |
| GET    | `/status/reset`        | Reset modem connection                          |

### API Examples (Python)

**Send SMS:**

```python
import requests
from requests.auth import HTTPBasicAuth

response = requests.post(
    'http://192.168.1.x:5000/sms',
    auth=HTTPBasicAuth('admin', 'password'),
    json={
        'text': 'Test message from Python',
        'number': '+420123456789'
    }
)
print(response.json())
```

**Get Modem Information:**

```python
# Get IMEI, manufacturer, model
response = requests.get(
    'http://192.168.1.x:5000/status/modem',
    auth=HTTPBasicAuth('admin', 'password')
)
print(response.json())
```

**Check SMS Storage Capacity:**

```python
# Get SIM storage usage
response = requests.get(
    'http://192.168.1.x:5000/status/sms_capacity',
    auth=HTTPBasicAuth('admin', 'password')
)
capacity = response.json()
print(f"SMS on SIM: {capacity['SIMUsed']}/{capacity['SIMSize']}")
```

**Delete All SMS:**

```python
# Clear all SMS from SIM card
response = requests.delete(
    'http://192.168.1.x:5000/sms/deleteall',
    auth=HTTPBasicAuth('admin', 'password')
)
print(response.json())
```

## 🔴 Troubleshooting

### Modem Not Detected

```bash
# Check USB devices
ls -la /dev/ttyUSB*

# Check kernel messages
dmesg | grep ttyUSB

# Restart add-on after connecting modem
```

### SMS Not Sending

1. **Check signal**: Should be > 20%
2. **Verify credit**: SIM card must have credit
3. **PIN code**: Either correct or disabled
4. **Network**: Check registration status

### Code 69 Error (SMSC)

- Add-on automatically uses Location 1 fallback
- Works the same as REST API
- No SMSC configuration needed

### MQTT Not Working

1. Verify MQTT broker is running
2. Check credentials
3. Look for connection errors in log
4. Ensure topic prefix doesn't conflict

### Text Fields Not Synchronized

- Add-on uses `retain=True` for synchronization
- Wait 2 seconds after restart for sync
- Phone number persists, message clears

## 💡 Tips & Tricks

### SMS Counter & Cost Tracking

Enable cost tracking by setting a price per SMS:

```yaml
sms_cost_per_message: 0.10 # e.g., $0.10 per SMS
sms_cost_currency: "USD"
```

This creates a `sensor.sms_gateway_total_cost` showing cumulative costs. Reset anytime using the **Reset Counter** button.

### Automatic SIM Storage Management

Prevent "SIM full" errors by auto-deleting read SMS:

```yaml
auto_delete_read_sms: true
```

SMS messages are automatically deleted after being read and published to MQTT. Storage capacity is tracked in `sensor.sms_gateway_sms_storage_used`.

### Monitor Modem Health

New sensors provide detailed diagnostics:

- `sensor.sms_gateway_modem_status` - Real-time connectivity (online/offline)
- `sensor.sms_gateway_modem_imei` - Device identification
- `sensor.sms_gateway_sim_imsi` - SIM card identification
- `sensor.sms_gateway_sms_storage_used` - Track SIM capacity usage

### Multiple Recipients (🆕 v2.1.1)

The addon supports multiple formats for sending to multiple recipients:

#### Format 1: Comma-separated string

```json
{
  "number": "+420111111111,+420222222222",
  "text": "Broadcast message"
}
```

#### Format 2: JSON array (Recommended)

```json
{
  "number": ["+420111111111", "+420222222222"],
  "text": "Broadcast message"
}
```

#### Using with rest_command

```yaml
rest_command:
  send_sms:
    url: "http://localhost:5000/sms"
    method: POST
    content_type: "application/json"
    username: "admin"
    password: "password"
    payload: '{"target": {{ target | tojson }}, "text": {{ message | tojson }}}'

# Then call with a list:
service: rest_command.send_sms
data:
  target:
    - "+420111111111"
    - "+420222222222"
  message: "Broadcast message"
```

### Unicode Support (Special Characters)

**MQTT Method (Automatic Detection):**
When sending SMS via MQTT, Unicode mode is automatically detected based on message content. If your message contains non-ASCII characters (háčky, čárky, emojis), Unicode encoding is automatically enabled.

```yaml
service: mqtt.publish
data:
  topic: "homeassistant/sensor/sms_gateway/send"
  payload: '{"number": "+420123456789", "text": "Příliš žluťoučký kůň"}'
  # Unicode automatically detected - no "unicode" parameter needed!
```

**REST API Method (Explicit Parameter):**
For REST API, you must explicitly set the `unicode` parameter:

```json
{
  "number": "+420123456789",
  "text": "Příliš žluťoučký kůň",
  "unicode": true
}
```

### Custom Notify Name

```yaml
notify:
  - name: Security_SMS
    platform: rest
    resource: http://192.168.1.x:5000/sms
    method: POST_JSON
    authentication: basic
    username: admin
    password: your_password
    target_param_name: number
    message_param_name: message
```

## 📝 Version History

See [CHANGELOG.md](./CHANGELOG.md) for complete version history and detailed changes.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/BigThunderSR/ha-legacy-gsm-sms/issues)
- **Repository**: [ha-legacy-gsm-sms](https://github.com/BigThunderSR/ha-legacy-gsm-sms)
- **Swagger UI**: <http://your-ha-ip:5000/docs/>
- **Original Projects**:
  - [PavelVe's SMS Gammu Gateway](https://github.com/PavelVe/hassio-addons)
  - [pajikos's sms-gammu-gateway](https://github.com/pajikos/sms-gammu-gateway)
