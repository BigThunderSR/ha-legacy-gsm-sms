"""Constants for legacy_gsm_sms Component."""

DOMAIN = "legacy_gsm_sms"
SMS_GATEWAY = "LEGACY_GSM_SMS_GATEWAY"
HASS_CONFIG = "legacy_gsm_sms_hass_config"
SMS_STATE_UNREAD = "UnRead"
SIGNAL_COORDINATOR = "signal_coordinator"
NETWORK_COORDINATOR = "network_coordinator"
SMS_COORDINATOR = "sms_coordinator"
GATEWAY = "gateway"
SMS_MANAGER = "sms_manager"
DEFAULT_SCAN_INTERVAL = 30
SMS_CHECK_INTERVAL = 10
CONF_BAUD_SPEED = "baud_speed"
CONF_UNICODE = "unicode"
DEFAULT_BAUD_SPEED = "0"

# Configuration options
CONF_SMS_CHECK_INTERVAL = "sms_check_interval"
CONF_AUTO_DELETE_READ_SMS = "auto_delete_read_sms"
CONF_SMS_HISTORY_MAX = "sms_history_max_messages"

DEFAULT_SMS_CHECK_INTERVAL = 10
DEFAULT_AUTO_DELETE_READ_SMS = True
DEFAULT_SMS_HISTORY_MAX = 10

# Events
EVENT_SMS_RECEIVED = f"{DOMAIN}.incoming_sms"

# Service constants
SERVICE_SEND_SMS = "send_sms"
SERVICE_DELETE_ALL_SMS = "delete_all_sms"
SERVICE_RESET_SENT_COUNTER = "reset_sent_counter"
SERVICE_RESET_RECEIVED_COUNTER = "reset_received_counter"

# Attribute constants
ATTR_NUMBER = "number"
ATTR_MESSAGE = "message"
ATTR_UNICODE = "unicode"
ATTR_FLASH = "flash"

# SMS Counter file paths (relative to HA config dir)
SMS_COUNTER_FILE = "sms_counter.json"
SMS_HISTORY_FILE = "sms_history.json"

DEFAULT_BAUD_SPEEDS = [
    {"value": DEFAULT_BAUD_SPEED, "label": "Auto"},
    {"value": "50", "label": "50"},
    {"value": "75", "label": "75"},
    {"value": "110", "label": "110"},
    {"value": "134", "label": "134"},
    {"value": "150", "label": "150"},
    {"value": "200", "label": "200"},
    {"value": "300", "label": "300"},
    {"value": "600", "label": "600"},
    {"value": "1200", "label": "1200"},
    {"value": "1800", "label": "1800"},
    {"value": "2400", "label": "2400"},
    {"value": "4800", "label": "4800"},
    {"value": "9600", "label": "9600"},
    {"value": "19200", "label": "19200"},
    {"value": "28800", "label": "28800"},
    {"value": "38400", "label": "38400"},
    {"value": "57600", "label": "57600"},
    {"value": "76800", "label": "76800"},
    {"value": "115200", "label": "115200"},
]
