#!/usr/bin/env python3
"""
SMS Gammu Gateway - Home Assistant Add-on
REST API SMS Gateway using python-gammu for USB GSM modems

Credits:
- Based on PavelVe's SMS Gammu Gateway (https://github.com/PavelVe/home-assistant-addons)
- Original project: pajikos/sms-gammu-gateway (https://github.com/pajikos/sms-gammu-gateway)
- Enhanced with network provider lookup and comprehensive diagnostics by BigThunderSR

Licensed under Apache License 2.0
"""

import os
import json
import logging
import signal
import sys
from flask import Flask, request
from flask_httpauth import HTTPBasicAuth
from flask_restx import Api, Resource, fields, reqparse

from support import init_state_machine, retrieveAllSms, deleteSms, encodeSms, set_network_type_cache_duration, invalidate_network_type_cache
from mqtt_publisher import MQTTPublisher
from gammu import GSMNetworks
from network_codes import get_network_name

# Configure logging with timestamp
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
mqtt_logger = logging.getLogger('mqtt_publisher')
mqtt_logger.setLevel(logging.INFO)

# Suppress Flask development server warnings
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Load version early for startup banner
VERSION = None  # Will be loaded properly later

# Monkey-patch click.echo to suppress Flask CLI startup messages
import click
_original_echo = click.echo
def _silent_echo(message=None, **kwargs):
    # Only suppress Flask's "Debug mode:" and "Serving Flask app" messages
    if message and isinstance(message, str):
        if 'Debug mode:' in message or 'Serving Flask app' in message:
            return
    _original_echo(message, **kwargs)
click.echo = _silent_echo

def load_version():
    """Load version from config.yaml"""
    try:
        # Try to read from addon info API first (most reliable in HA)
        supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "")
        if supervisor_token:
            try:
                import requests
                response = requests.get('http://supervisor/addons/self/info',
                                       headers={'Authorization': f'Bearer {supervisor_token}'},
                                       timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    logging.debug(f"Supervisor API response: {data}")
                    # The structure might be: {'result': 'ok', 'data': {'version': 'x.x.x'}}
                    # or just: {'data': {'version': 'x.x.x'}}
                    if 'data' in data and 'version' in data['data']:
                        version = data['data']['version']
                        if version and version != 'unknown':
                            logging.debug(f"Got version from Supervisor API: {version}")
                            return version
            except Exception as e:
                logging.debug(f"Supervisor API failed: {e}")
                pass

        # Fallback: try to read from config.yaml in multiple locations
        possible_paths = [
            '/config.yaml',  # Root location when copied to container
            os.path.join(os.path.dirname(__file__), 'config.yaml'),  # Same directory as run.py
            '/data/../config.yaml',  # Relative to data directory
        ]
        
        import yaml
        for config_yaml_path in possible_paths:
            logging.debug(f"Trying to read version from: {config_yaml_path}")
            if os.path.exists(config_yaml_path):
                with open(config_yaml_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    version = config_data.get('version')
                    if version:
                        logging.debug(f"Got version from {config_yaml_path}: {version}")
                        return version

        logging.warning("Could not find version in any location")
        return "unknown"
    except Exception as e:
        logging.warning(f"Could not read version: {e}")
        return "unknown"

def load_ha_config():
    """Load Home Assistant add-on configuration"""
    config_path = '/data/options.json'
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    else:
        # Default values for testing outside HA
        return {
            'device_path': '/dev/ttyUSB0',
            'pin': '',
            'port': 5000,
            'ssl': False,
            'username': 'admin',
            'password': 'password',
            'mqtt_enabled': True,
            'mqtt_host': 'localhost',
            'mqtt_port': 1883,
            'mqtt_username': '',
            'mqtt_password': '',
            'mqtt_topic_prefix': 'homeassistant/sensor/sms_gateway',
            'sms_monitoring_enabled': True,
            'sms_check_interval': 60,
            'sms_cost_per_message': 0.0,
            'sms_cost_currency': 'CZK',
            'auto_delete_read_sms': False
        }

# Helper function for IP whitelist checking
def is_ip_allowed(client_ip, allowed_networks):
    """Check if client IP is in allowed network ranges"""
    import ipaddress
    try:
        client = ipaddress.ip_address(client_ip)
        for network_str in allowed_networks:
            try:
                network = ipaddress.ip_network(network_str, strict=False)
                if client in network:
                    return True
            except ValueError:
                logging.warning(f"Invalid network in whitelist: {network_str}")
        return False
    except ValueError:
        logging.error(f"Invalid client IP: {client_ip}")
        return False

# Load version and configuration
VERSION = load_version()
config = load_ha_config()

# Configure logging level based on config
log_level = config.get('log_level', 'info')
if log_level == 'debug':
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info("🔍 Logging level set to DEBUG (all messages)")
elif log_level == 'warning':
    logging.getLogger().setLevel(logging.WARNING)
    logging.warning("⚠️  Logging level set to WARNING (warnings and errors only)")
else:  # info
    logging.getLogger().setLevel(logging.INFO)
    logging.info("ℹ️  Logging level set to INFO (standard messages)")

# Log version at startup
logging.info(f"GSM SMS Gateway Enhanced v{VERSION}")

pin = config.get('pin') if config.get('pin') else None
ssl = config.get('ssl', False)
port = config.get('port', 5000)
username = config.get('username', 'admin')
password = config.get('password', 'password')
device_path = config.get('device_path', '/dev/ttyUSB0')

# GET endpoint security settings
get_endpoint_auth_required = config.get('get_endpoint_auth_required', False)
get_endpoint_allowed_ips = config.get('get_endpoint_allowed_ips', [])
get_endpoint_deduplication_enabled = config.get('get_endpoint_deduplication_enabled', True)
logging.info(
    f"🔒 GET endpoint auth: {'REQUIRED' if get_endpoint_auth_required else 'DISABLED'}"
)
if get_endpoint_allowed_ips:
    logging.info(f"🌐 GET endpoint IP whitelist: {get_endpoint_allowed_ips}")
logging.info(
    f"🔄 GET endpoint deduplication: {'ENABLED' if get_endpoint_deduplication_enabled else 'DISABLED'}"
)

# SMS deduplication cache for GET endpoint (prevents device retries)
# Format: {"number|text": timestamp}
_sms_dedup_cache = {}
_sms_dedup_window = 15  # seconds

# Configure network type cache duration
network_type_cache_seconds = config.get('network_type_cache_seconds', 300)
set_network_type_cache_duration(network_type_cache_seconds)

# Log device path and check accessibility
logging.info(f"📱 Configured device path: {device_path}")

# Check if it's a by-id symlink
if '/dev/serial/by-id/' in device_path:
    if os.path.islink(device_path):
        resolved_path = os.path.realpath(device_path)
        logging.info(f"🔗 By-ID symlink resolves to: {resolved_path}")
        
        # Check if resolved device exists and is accessible
        if os.path.exists(resolved_path):
            logging.info(f"✅ Resolved device {resolved_path} is accessible")
        else:
            logging.error(f"❌ ERROR: Resolved device {resolved_path} is NOT accessible!")
            logging.error(f"💡 TIP: Add '{resolved_path}' to the 'devices' list in config.yaml")
    else:
        logging.error(f"❌ ERROR: {device_path} is not a valid symlink!")
        if not os.path.exists(device_path):
            logging.error(f"💡 TIP: Check if /dev/serial/by-id is mounted (add to 'devices' list)")
elif os.path.exists(device_path):
    logging.info(f"✅ Device {device_path} is accessible")
else:
    logging.error(f"❌ ERROR: Device {device_path} is NOT accessible!")
    logging.error(f"💡 TIP: Add '{device_path}' to the 'devices' list in config.yaml")

# Initialize MQTT publisher FIRST (before gammu)
mqtt_publisher = MQTTPublisher(config)

# Publish OFFLINE status immediately on startup (clears any stale "online" state)
if mqtt_publisher.connected:
    mqtt_publisher.device_tracker.initial_check_done = False  # Force offline
    mqtt_publisher.publish_device_status()
    logging.info("📡 Published initial OFFLINE status on startup")

# Now initialize gammu state machine (this may fail if modem not connected)
logging.info(f"🔌 Attempting to initialize Gammu with device: {device_path}")
machine = init_state_machine(pin, device_path)

# Set gammu machine for MQTT SMS sending
mqtt_publisher.set_gammu_machine(machine)

# Setup signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals (SIGTERM, SIGINT)"""
    logging.info(f"🛑 Received shutdown signal {signum}, publishing offline status...")
    try:
        mqtt_publisher.disconnect()
        logging.info("✅ MQTT disconnected successfully")
    except Exception as e:
        logging.error(f"❌ Error during MQTT disconnect: {e}")
    finally:
        sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Register atexit handler as backup
import atexit
def cleanup():
    """Cleanup function called on normal exit"""
    logging.info("🧹 Cleanup: Publishing offline status...")
    try:
        mqtt_publisher.disconnect()
    except Exception as e:
        logging.error(f"Error during cleanup: {e}")

atexit.register(cleanup)

app = Flask(__name__)

# Check if running under Ingress
import os
ingress_path = os.environ.get('INGRESS_PATH', '')

# Create simple HTML page for Ingress
@app.route('/')
def home():
    """Simple status page for Home Assistant Ingress"""
    from flask import Response, request
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>SMS Gammu Gateway</title>
        <meta charset="utf-8">
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                margin: 0;
                padding: 40px 20px;
                background: #f5f5f5;
                text-align: center;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                background: white;
                padding: 40px;
                border-radius: 15px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
                font-size: 2.2em;
            }
            .status {
                background: #e8f5e9;
                border: 2px solid #4caf50;
                padding: 20px;
                margin: 30px 0;
                border-radius: 10px;
                font-size: 1.2em;
            }
            .swagger-link {
                display: inline-block;
                padding: 15px 30px;
                background: #2196F3;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin: 20px 0;
                font-size: 1.1em;
                font-weight: bold;
            }
            .swagger-link:hover {
                background: #1976D2;
            }
            .info {
                background: #f0f8ff;
                border-left: 4px solid #2196F3;
                padding: 15px;
                margin: 20px 0;
                text-align: left;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📱 SMS Gammu Gateway</h1>
            
            <div class="status">
                <strong>✅ Gateway is running properly</strong><br>
                Version: {VERSION}
            </div>
            
            <a href="http://''' + request.host.split(':')[0] + ''':5000/docs/" 
               class="swagger-link" target="_blank">
                📋 Open Swagger API Documentation
            </a>
            
            <div class="info">
                <strong>REST API Endpoints:</strong><br>
                • GET /status/signal - Signal strength<br>
                • GET /status/network - Network information<br>
                • POST /sms - Send SMS (requires authentication)<br>
                • GET /sms - Get all SMS (requires authentication)<br>
                • GET /sms/{PHONE}&{MESSAGE} - Send SMS via GET (legacy compatibility, optional auth)<br>
                <br>
                <strong>Authentication in Swagger UI:</strong><br>
                1. Click the "Authorize" button 🔒 in the top right corner<br>
                2. Enter Username and Password from add-on configuration<br>
                3. Click "Authorize" - now you can test protected endpoints
            </div>
        </div>
    </body>
    </html>
    '''
    return Response(html.replace('{VERSION}', VERSION), mimetype='text/html')

# Swagger UI Configuration
# Put Swagger UI on /docs/ path for direct access via port 5000
api = Api(
    app,
    version=VERSION,
    title='SMS Gammu Gateway API',
    description='REST API for sending and receiving SMS messages via USB GSM modems (SIM800L, Huawei, etc.). Modern replacement for deprecated SMS notifications via GSM-modem integration.',
    doc='/docs/',  # Swagger UI on /docs/ path
    prefix='',
    authorizations={
        'basicAuth': {
            'type': 'basic',
            'in': 'header',
            'name': 'Authorization'
        }
    },
    security='basicAuth'
)

auth = HTTPBasicAuth()

@auth.verify_password
def verify(user, pwd):
    if not (user and pwd):
        return False
    return user == username and pwd == password

# API Models for Swagger documentation
sms_model = api.model('SMS', {
    'text': fields.String(required=True, description='SMS message text', example='Hello, how are you?'),
    'number': fields.String(required=True, description='Phone number (international format)', example='+420123456789'),
    'smsc': fields.String(required=False, description='SMS Center number (optional)', example='+420603052000'),
    'unicode': fields.Boolean(required=False, description='Use Unicode encoding', default=False),
    'flash': fields.Boolean(required=False, description='Send as Flash SMS (displays on screen, not saved)', default=False)
})

sms_response = api.model('SMS Response', {
    'Date': fields.String(description='Date and time received', example='2025-01-19 14:30:00'),
    'Number': fields.String(description='Sender phone number', example='+420123456789'),
    'State': fields.String(description='SMS state', example='UnRead'),
    'Text': fields.String(description='SMS message text', example='Hello World!')
})

signal_response = api.model('Signal Quality', {
    'SignalStrength': fields.Integer(description='Signal strength in dBm', example=-75),
    'SignalPercent': fields.Integer(description='Signal strength percentage', example=65),
    'BitErrorRate': fields.Integer(description='Bit error rate', example=-1)
})

network_response = api.model('Network Info', {
    'NetworkName': fields.String(description='Network operator name', example='T-Mobile'),
    'State': fields.String(description='Network registration state', example='HomeNetwork'),
    'NetworkCode': fields.String(description='Network operator code', example='230 01'),
    'CID': fields.String(description='Cell ID', example='0A1B2C3D'),
    'LAC': fields.String(description='Location Area Code', example='1234')
})

send_response = api.model('Send Response', {
    'status': fields.Integer(description='HTTP status code', example=200),
    'message': fields.String(description='Response message', example='[1]')
})

reset_response = api.model('Reset Response', {
    'status': fields.Integer(description='HTTP status code', example=200),
    'message': fields.String(description='Reset message', example='Reset done')
})

modem_info_response = api.model('Modem Info', {
    'IMEI': fields.String(description='Modem IMEI number', example='123456789012345'),
    'Manufacturer': fields.String(description='Modem manufacturer', example='Huawei'),
    'Model': fields.String(description='Modem model', example='E3372'),
    'Firmware': fields.String(description='Firmware version', example='22.323.62.00.143')
})

sim_info_response = api.model('SIM Info', {
    'IMSI': fields.String(description='SIM IMSI number', example='230011234567890')
})

sms_capacity_response = api.model('SMS Capacity', {
    'SIMUsed': fields.Integer(description='SMS count in SIM memory', example=5),
    'SIMSize': fields.Integer(description='SIM total capacity', example=50),
    'PhoneUsed': fields.Integer(description='SMS count in phone memory', example=0),
    'PhoneSize': fields.Integer(description='Phone memory capacity', example=100),
    'TemplatesUsed': fields.Integer(description='SMS templates used', example=0)
})

# API Namespaces
ns_sms = api.namespace('sms', description='SMS operations (requires authentication)')
ns_status = api.namespace('status', description='Device status and information (public)')

@ns_sms.route('')
@ns_sms.doc('sms_operations')
class SmsCollection(Resource):
    @ns_sms.doc('get_all_sms')
    @ns_sms.marshal_list_with(sms_response, code=200)
    @ns_sms.doc(security='basicAuth')
    @auth.login_required
    def get(self):
        """Get all SMS messages from SIM/device memory"""
        allSms = mqtt_publisher.track_gammu_operation("retrieveAllSms", retrieveAllSms, machine)
        list(map(lambda sms: sms.pop("Locations", None), allSms))
        return allSms

    @ns_sms.doc('send_sms')
    @ns_sms.expect(sms_model)
    @ns_sms.marshal_with(send_response, code=200)
    @ns_sms.doc(security='basicAuth')
    @auth.login_required
    def post(self):
        """Send SMS message(s)"""
        # Support both JSON and form-encoded data
        # Check Content-Type to decide how to parse request
        content_type = request.content_type or ''
        
        if 'application/json' in content_type:
            # JSON request - use get_json()
            data = request.get_json() or {}
        elif 'application/x-www-form-urlencoded' in content_type or 'multipart/form-data' in content_type:
            # Form-encoded request - use form data
            data = dict(request.form)
            # Convert boolean strings to actual booleans
            if 'unicode' in data:
                data['unicode'] = data['unicode'].lower() in ('true', '1', 'yes')
            if 'flash' in data:
                data['flash'] = data['flash'].lower() in ('true', '1', 'yes')
        else:
            # Try both methods as fallback
            data = request.get_json(silent=True) or {}
            if not data:
                # Fall back to form data
                data = dict(request.form)
        
        # If still no data, try query parameters as last resort
        if not data:
            parser = reqparse.RequestParser()
            parser.add_argument('text', required=False, help='SMS message text')
            parser.add_argument('message', required=False, help='SMS message text (alias for text)')
            parser.add_argument('number', required=False, help='Phone number(s), comma separated')
            parser.add_argument('target', required=False, help='Phone number (alias for number)')
            parser.add_argument('smsc', required=False, help='SMS Center number (optional)')
            parser.add_argument('unicode', type=bool, required=False, default=None, help='Use Unicode encoding (auto-detect if not specified)')
            parser.add_argument('flash', type=bool, required=False, default=False, help='Send as Flash SMS')
            data = parser.parse_args()
        # Note: Don't set unicode default here - let auto-detection handle it
        
        # Support both 'text' and 'message' parameters
        sms_text = data.get('text') or data.get('message')
        if not sms_text:
            return {"status": 400, "message": "Missing required field: text or message"}, 400
        
        # Support both 'number' and 'target' parameters
        sms_number = data.get('number') or data.get('target')
        if not sms_number:
            return {"status": 400, "message": "Missing required field: number or target"}, 400
        
        logging.info(f"SMS send request - Text: '{sms_text}', Numbers: '{sms_number}', Type: {type(sms_number)}")
        
        # Handle both string (comma-separated) and list formats
        if isinstance(sms_number, list):
            numbers = sms_number
        else:
            # Check if it's a string representation of a list (e.g., "['phone1', 'phone2']")
            sms_number_str = str(sms_number).strip()
            if sms_number_str.startswith('[') and sms_number_str.endswith(']'):
                try:
                    # Try to parse as JSON array first
                    import json
                    numbers = json.loads(sms_number_str)
                except:
                    # If JSON parsing fails, try Python literal eval
                    try:
                        import ast
                        numbers = ast.literal_eval(sms_number_str)
                    except:
                        # Fall back to treating as single number
                        numbers = [sms_number_str]
            else:
                # Comma-separated string
                numbers = [n.strip() for n in sms_number_str.split(',')]
        
        # Auto-detect unicode if not explicitly specified
        # This matches the behavior of MQTT send methods
        unicode_mode = data.get('unicode')
        if unicode_mode is None:
            # Auto-detect: check if text contains non-ASCII characters (emojis, etc.)
            try:
                sms_text.encode('ascii')
                unicode_mode = False
            except UnicodeEncodeError:
                unicode_mode = True
                logging.info("🔤 Auto-detected Unicode mode for non-ASCII text")

        # Determine SMS class based on flash parameter
        flash_mode = data.get('flash', False)
        sms_class = 0 if flash_mode else -1
        if flash_mode:
            logging.info("⚡ Sending Flash SMS (will display on screen without saving)")

        smsinfo = {
            "Class": sms_class,
            "Unicode": unicode_mode,
            "Entries": [
                {
                    "ID": "ConcatenatedTextLong",
                    "Buffer": sms_text,
                }
            ],
        }
        
        # Get cached SMSC for reliable sending
        cached_smsc = mqtt_publisher.get_cached_smsc()
        
        messages = []
        for number in numbers:
            for message in encodeSms(smsinfo):
                # Use cached SMSC if available (more reliable)
                if data.get("smsc"):
                    message["SMSC"] = {'Number': data.get("smsc")}
                elif cached_smsc:
                    message["SMSC"] = {'Number': cached_smsc}
                else:
                    message["SMSC"] = {'Location': 1}
                
                message["Number"] = number.strip()
                messages.append(message)
        
        # Send SMS with automatic retry on recoverable errors
        # Queue SMS BEFORE sending to survive restarts during send/retry
        results = []
        for message in messages:
            number = message["Number"]
            # Get SMSC for potential queue
            smsc = None
            if message.get("SMSC") and message["SMSC"].get("Number"):
                smsc = message["SMSC"]["Number"]
            
            # Queue SMS first to survive restarts during send attempt
            mqtt_publisher.queue_sms_for_retry(number, sms_text, smsc)
            
            try:
                mqtt_publisher.track_gammu_operation(
                    "SendSMS", machine.SendSMS, message
                )
                # Success - remove from queue
                mqtt_publisher.sms_queue.remove(number, sms_text)
                results.append(number)
                mqtt_publisher.sms_counter.increment()
            except Exception as e:
                # Check if recoverable error was detected and reset triggered
                if getattr(e, 'err_recoverable_detected', False):
                    logging.warning(
                        f"🔄 Retrying SMS to {number} "
                        "after modem reconnect..."
                    )
                    time.sleep(5)  # Additional wait after reconnect
                    try:
                        # Use publisher's gammu_machine (may have been reconnected)
                        mqtt_publisher.track_gammu_operation(
                            "SendSMS",
                            mqtt_publisher.gammu_machine.SendSMS,
                            message
                        )
                        # Success - remove from queue
                        mqtt_publisher.sms_queue.remove(number, sms_text)
                        results.append(number)
                        mqtt_publisher.sms_counter.increment()
                        logging.info(
                            f"✅ SMS sent to {number} after retry"
                        )
                    except Exception as retry_error:
                        # Final failure - already in queue, just log
                        logging.error(
                            f"❌ SMS retry failed for {number}: {retry_error}"
                        )
                        logging.info(
                            f"📥 SMS to {number} remains queued for later"
                        )
                        # Don't raise - continue with other messages
                else:
                    # Non-recoverable error - already in queue, just log
                    logging.error(f"❌ SMS failed for {number}: {e}")
                    logging.info(f"📥 SMS to {number} remains queued for later")
                    # Don't raise - continue with other messages
        
        mqtt_publisher.publish_sms_counter()
        
        # Build response message
        total_numbers = len(set([m["Number"] for m in messages]))
        sent_count = len(results)
        queued_count = total_numbers - sent_count
        
        if queued_count > 0:
            msg = f"Sent to {sent_count} number(s), {queued_count} queued for retry"
            return {"status": 200, "message": msg}, 200
        else:
            return {"status": 200, "message": f"Sent to {sent_count} number(s)"}, 200


@ns_sms.route('/add/<path:sms_data>')
@ns_sms.route('/<path:sms_data>')
@ns_sms.doc('send_sms_get')
class SmsGet(Resource):
    @ns_sms.doc('send_sms_via_get')
    @ns_sms.doc(
        params={
            'sms_data': {
                'description': 'Phone number and message format: {PHONE}&{MESSAGE}',
                'type': 'string',
                'example': '5555551234&Test+message'
            }
        },
        description='''
        Add/Send SMS via GET request with data in URL path - designed for legacy devices.
        
        📱 **Format:** GET /sms/add/{PHONE_NUMBER}&{MESSAGE} (or /sms/{PHONE_NUMBER}&{MESSAGE})
        
        📋 **Try These Examples:**
        • Basic: /sms/add/5555551234&Test+message
        • International: /sms/add/%2B15555551234&Hello%20World
        • Special chars: /sms/add/5555551234&Message+with+%26+special+chars
        • Legacy path: /sms/5555551234&Test+message (backward compatible)
        
        🔒 **Security (Configurable):**
        • IP Whitelisting: Only allowed IPs can access (default: private networks only)
        • Optional Authentication: Can require HTTP Basic Auth (disabled by default)
        • Deduplication: Prevents duplicate SMS within 15-second window (enabled by default)
        
        ⚙️ **Configuration Options:**
        • get_endpoint_auth_required (default: false) - Toggle authentication
        • get_endpoint_allowed_ips (default: private networks) - CIDR IP whitelist
        • get_endpoint_deduplication_enabled (default: true) - Duplicate prevention
        
        📝 **Notes:**
        • Available paths: /sms/add/{data} (recommended) or /sms/{data} (legacy)
        • URL encoding: Use + or %20 for spaces, %2B for + in phone numbers
        • Authentication disabled by default for legacy device compatibility
        • Use POST /sms for authenticated requests in modern applications
        • Deduplication uses: {phone}|{message} as cache key
        '''
    )
    @ns_sms.response(200, 'SMS sent successfully', send_response)
    @ns_sms.response(400, 'Invalid request format')
    @ns_sms.response(401, 'Authentication required')
    @ns_sms.response(403, 'IP address not authorized')
    def get(self, sms_data):
        """Send SMS via GET request (legacy compatibility)"""
        # Check IP whitelist
        client_ip = request.remote_addr
        if get_endpoint_allowed_ips:
            if not is_ip_allowed(client_ip, get_endpoint_allowed_ips):
                logging.warning(
                    f"🚫 Access denied from {client_ip} "
                    f"(not in whitelist)"
                )
                return {
                    'status': 403,
                    'message': 'Access denied - IP not authorized'
                }, 403
        
        # Check auth if required
        if get_endpoint_auth_required:
            auth_header = request.headers.get('Authorization')
            if not auth_header:
                logging.warning(
                    f"🔒 Unauthorized GET request from {client_ip}"
                )
                return {
                    'status': 401,
                    'message': 'Authentication required'
                }, 401
            
            # Verify Basic Auth
            try:
                import base64
                auth_type, credentials = auth_header.split(' ', 1)
                if auth_type.lower() != 'basic':
                    return {'status': 401, 'message': 'Invalid auth'}, 401
                
                decoded = base64.b64decode(credentials).decode('utf-8')
                provided_user, provided_pass = decoded.split(':', 1)
                
                if provided_user != username or provided_pass != password:
                    logging.warning(f"🔒 Invalid credentials from {client_ip}")
                    return {'status': 401, 'message': 'Invalid credentials'}, 401
            except Exception as e:
                logging.error(f"Auth error: {e}")
                return {'status': 401, 'message': 'Auth error'}, 401
        
        # Parse path: {PHONE}&{MESSAGE}
        if '&' not in sms_data:
            return {
                "status": 400, 
                "message": "Invalid format. Use: /sms/{PHONE}&{MESSAGE}"
            }, 400
        
        # Split on first &
        parts = sms_data.split('&', 1)
        if len(parts) != 2:
            return {
                "status": 400,
                "message": "Invalid format. Use: /sms/{PHONE}&{MESSAGE}"
            }, 400
        
        sms_number = parts[0].strip()
        sms_text = parts[1].strip()
        
        # URL decode (replace + with space, etc.)
        from urllib.parse import unquote_plus
        sms_number = unquote_plus(sms_number)
        sms_text = unquote_plus(sms_text)
        
        if not sms_number or not sms_text:
            return {
                "status": 400,
                "message": "Phone number and message cannot be empty"
            }, 400
        
        logging.info(f"📨 GET SMS request - Number: '{sms_number}', Text: '{sms_text}'")
        
        # Check for duplicate request (device retry) if enabled
        import time
        dedup_key = f"{sms_number}|{sms_text}"
        current_time = time.time()
        
        if get_endpoint_deduplication_enabled:
            # Clean old entries from cache
            global _sms_dedup_cache
            _sms_dedup_cache = {k: v for k, v in _sms_dedup_cache.items() 
                                if current_time - v < _sms_dedup_window}
            
            # Check if this SMS was just sent
            if dedup_key in _sms_dedup_cache:
                time_since = current_time - _sms_dedup_cache[dedup_key]
                logging.info(
                    f"⏭️  Skipping duplicate SMS to {sms_number} "
                    f"(sent {time_since:.1f}s ago)"
                )
                return {
                    "status": 200,
                    "message": f"SMS already sent to {sms_number} recently"
                }, 200
        
        # Encode and send SMS (same logic as POST)
        try:
            # Auto-detect unicode
            try:
                sms_text.encode('ascii')
                unicode_mode = False
            except UnicodeEncodeError:
                unicode_mode = True
            
            # Build smsinfo dict (same as POST endpoint)
            smsinfo = {
                "Class": -1,  # Normal SMS
                "Unicode": unicode_mode,
                "Entries": [
                    {
                        "ID": "ConcatenatedTextLong",
                        "Buffer": sms_text,
                    }
                ],
            }
            
            # Get cached SMSC for reliable sending
            cached_smsc = mqtt_publisher.get_cached_smsc()
            
            # Encode SMS (returns list of message parts)
            messages = []
            for message in encodeSms(smsinfo):
                if cached_smsc:
                    message["SMSC"] = {'Number': cached_smsc}
                else:
                    message["SMSC"] = {'Location': 1}
                message["Number"] = sms_number
                messages.append(message)
            
            # Validate we got messages
            if not messages:
                raise ValueError("encodeSms returned no messages")
            
            # Queue SMS first
            smsc = messages[0].get("SMSC", {}).get("Number")
            mqtt_publisher.queue_sms_for_retry(sms_number, sms_text, smsc)
            
            # Send all message parts
            for message in messages:
                mqtt_publisher.track_gammu_operation("SendSMS", machine.SendSMS, message)
            
            # Success - remove from queue
            mqtt_publisher.sms_queue.remove(sms_number, sms_text)
            mqtt_publisher.sms_counter.increment()
            mqtt_publisher.publish_sms_counter()
            
            # Add to deduplication cache if enabled
            if get_endpoint_deduplication_enabled:
                _sms_dedup_cache[dedup_key] = current_time
            
            logging.info(f"✅ SMS sent via GET to {sms_number}")
            
            return {
                "status": 200,
                "message": f"SMS sent to {sms_number}"
            }, 200
            
        except Exception as e:
            logging.error(f"❌ GET SMS failed for {sms_number}: {e}")
            return {
                "status": 500,
                "message": f"Failed to send SMS: {str(e)}"
            }, 500

@ns_sms.route('/getsms')
@ns_sms.doc('get_and_delete_first_sms')
class GetSms(Resource):
    @ns_sms.doc('pop_first_sms')
    @ns_sms.marshal_with(sms_response, code=200)
    @ns_sms.doc(security='basicAuth')
    @auth.login_required
    def get(self):
        """Get first SMS and delete it from memory"""
        allSms = mqtt_publisher.track_gammu_operation("retrieveAllSms", retrieveAllSms, machine)
        sms = {"Date": "", "Number": "", "State": "", "Text": ""}
        if len(allSms) > 0:
            sms = allSms[0]
            mqtt_publisher.track_gammu_operation("deleteSms", deleteSms, machine, sms)
            sms.pop("Locations", None)
            # Publish to MQTT if enabled and SMS has content
            if sms.get("Text"):
                mqtt_publisher.publish_sms_received(sms)
        return sms

@ns_sms.route('/deleteall')
@ns_sms.doc('delete_all_sms')
class DeleteAllSms(Resource):
    @ns_sms.doc('delete_all_messages')
    @ns_sms.doc(security='basicAuth')
    @auth.login_required
    def delete(self):
        """Delete all SMS messages from SIM/device memory"""
        allSms = mqtt_publisher.track_gammu_operation("retrieveAllSms", retrieveAllSms, machine)
        count = len(allSms)
        for sms in allSms:
            mqtt_publisher.track_gammu_operation("deleteSms", deleteSms, machine, sms)
        return {"status": 200, "message": f"Deleted {count} SMS messages"}, 200

@ns_sms.route('/<int:id>')
@ns_sms.doc('sms_by_id')
class SmsItem(Resource):
    @ns_sms.doc('get_sms_by_id')
    @ns_sms.marshal_with(sms_response, code=200)
    @ns_sms.doc(security='basicAuth')
    @auth.login_required
    def get(self, id):
        """Get specific SMS by ID"""
        allSms = mqtt_publisher.track_gammu_operation("retrieveAllSms", retrieveAllSms, machine)
        if id < 0 or id >= len(allSms):
            api.abort(404, f"SMS with id '{id}' not found")
        sms = allSms[id]
        sms.pop("Locations", None)
        return sms

    @ns_sms.doc('delete_sms_by_id')
    @ns_sms.doc(security='basicAuth')
    @auth.login_required
    def delete(self, id):
        """Delete SMS by ID"""
        allSms = mqtt_publisher.track_gammu_operation("retrieveAllSms", retrieveAllSms, machine)
        if id < 0 or id >= len(allSms):
            api.abort(404, f"SMS with id '{id}' not found")
        mqtt_publisher.track_gammu_operation("deleteSms", deleteSms, machine, allSms[id])
        return '', 204

@ns_status.route('/signal')
@ns_status.doc('get_signal_quality')
class Signal(Resource):
    @ns_status.doc('signal_strength')
    @ns_status.marshal_with(signal_response)
    def get(self):
        """Get GSM signal strength and quality"""
        signal_data = mqtt_publisher.track_gammu_operation("GetSignalQuality", machine.GetSignalQuality)
        # Publish to MQTT if enabled
        mqtt_publisher.publish_signal_strength(signal_data)
        return signal_data

@ns_status.route('/network')
@ns_status.doc('get_network_info')
class Network(Resource):
    # Cache for last known numeric network code (for MVNO name handling)
    _last_network_code = None
    
    @ns_status.doc('network_information')
    @ns_status.marshal_with(network_response)
    def get(self):
        """Get network operator and registration information"""
        network = mqtt_publisher.track_gammu_operation("GetNetworkInfo", machine.GetNetworkInfo)
        raw_network_name = network.get("NetworkName")
        network_code = network.get("NetworkCode", "")
        network_name = raw_network_name
        resolved_code = None
        
        # Handle modem quirk: Some modems put operator name (e.g., "Red Pocket") in NetworkCode field
        if network_code:
            if network_code.isdigit():
                # Numeric MCC+MNC code (e.g., "310260")
                resolved_code = network_code
                if not network_name or not network_name.strip():
                    # Lookup name from database if NetworkName is empty
                    network_name = get_network_name(network_code)
                    if not network_name:
                        network_name = GSMNetworks.get(network_code, 'Unknown')
            else:
                # Operator name in NetworkCode field (e.g., "Red Pocket", "Xfinity Mobile")
                if not network_name or not network_name.strip():
                    network_name = network_code
                
                # Try reverse lookup: find numeric code for this operator name
                from network_codes import NETWORK_OPERATORS
                for code, name in NETWORK_OPERATORS.items():
                    if name.lower() == network_code.lower():
                        resolved_code = code
                        break
                
                # If reverse lookup fails, use cached code from previous poll
                if not resolved_code and Network._last_network_code:
                    resolved_code = Network._last_network_code
        
        # Cache the numeric code for next time (when modem reports operator name)
        if resolved_code:
            Network._last_network_code = resolved_code
        
        # Update network dict with resolved values
        network["NetworkCode"] = resolved_code
        network["NetworkName"] = network_name or 'Unknown'
        
        # Map Gammu's state to human-readable format
        state = network.get("State", "Unknown")
        state_map = {
            "HomeNetwork": "Registered (Home)",
            "RoamingNetwork": "Registered (Roaming)",
            "RequestingNetwork": "Searching",
            "RegistrationDenied": "Registration Denied",
            "NoNetwork": "Not Registered",
            "Unknown": "Unknown",
        }
        network["State"] = state_map.get(state, state)
        
        # Publish to MQTT if enabled
        mqtt_publisher.publish_network_info(network)
        return network

@ns_status.route('/modem')
@ns_status.doc('get_modem_info')
class ModemInfo(Resource):
    @ns_status.doc('modem_information')
    @ns_status.marshal_with(modem_info_response)
    def get(self):
        """Get modem hardware information (IMEI, manufacturer, model, firmware)"""
        try:
            modem_info = {
                "IMEI": mqtt_publisher.track_gammu_operation("GetIMEI", machine.GetIMEI),
                "Manufacturer": mqtt_publisher.track_gammu_operation("GetManufacturer", machine.GetManufacturer),
                "Model": mqtt_publisher.track_gammu_operation("GetModel", machine.GetModel)
            }
            try:
                # Firmware can fail on some modems
                modem_info["Firmware"] = mqtt_publisher.track_gammu_operation("GetFirmware", machine.GetFirmware)[0]
            except:
                modem_info["Firmware"] = "Unknown"

            # Publish to MQTT if enabled
            mqtt_publisher.publish_modem_info(modem_info)
            return modem_info
        except Exception as e:
            api.abort(500, f"Failed to get modem info: {str(e)}")

@ns_status.route('/sim')
@ns_status.doc('get_sim_info')
class SimInfo(Resource):
    @ns_status.doc('sim_information')
    @ns_status.marshal_with(sim_info_response)
    def get(self):
        """Get SIM card information (IMSI)"""
        try:
            sim_info = {
                "IMSI": mqtt_publisher.track_gammu_operation("GetSIMIMSI", machine.GetSIMIMSI)
            }
            # Publish to MQTT if enabled
            mqtt_publisher.publish_sim_info(sim_info)
            return sim_info
        except Exception as e:
            api.abort(500, f"Failed to get SIM info: {str(e)}")

@ns_status.route('/sms_capacity')
@ns_status.doc('get_sms_capacity')
class SmsCapacity(Resource):
    @ns_status.doc('sms_storage_capacity')
    @ns_status.marshal_with(sms_capacity_response)
    def get(self):
        """Get SMS storage capacity and usage"""
        try:
            capacity = mqtt_publisher.track_gammu_operation("GetSMSStatus", machine.GetSMSStatus)
            # Publish to MQTT if enabled
            mqtt_publisher.publish_sms_capacity(capacity)
            return capacity
        except Exception as e:
            api.abort(500, f"Failed to get SMS capacity: {str(e)}")

@ns_status.route('/reset')
@ns_status.doc('reset_modem')
class Reset(Resource):
    @ns_status.doc('modem_reset')
    @ns_status.marshal_with(reset_response)
    def get(self):
        """Reset GSM modem (useful for stuck connections)"""
        mqtt_publisher.track_gammu_operation("Reset", machine.Reset, False)
        return {"status": 200, "message": "Reset done"}, 200

if __name__ == '__main__':
    print(f"🚀 SMS Gammu Gateway v{VERSION} started successfully!")
    print(f"📱 Device: {device_path}")
    print(f"🌐 API available on port {port}")
    print(f"🏠 Web UI: http://localhost:{port}/")
    print(f"🔒 SSL: {'Enabled' if ssl else 'Disabled'}")
    
    # MQTT info
    if config.get('mqtt_enabled', False):
        print(f"📡 MQTT: Enabled -> {config.get('mqtt_host')}:{config.get('mqtt_port')}")
        
        # Wait a moment for MQTT connection, then publish initial states
        import time
        time.sleep(2)
        mqtt_publisher.publish_initial_states_with_machine(machine)
        
        # Start periodic MQTT publishing
        status_interval = config.get('status_update_interval', 300)
        mqtt_publisher.publish_status_periodic(machine, interval=status_interval)
        print(f"📊 Status Updates: Every {status_interval}s (signal, network)")
        
        # Start SMS monitoring if enabled
        if config.get('sms_monitoring_enabled', True):
            check_interval = config.get('sms_check_interval', 60)
            mqtt_publisher.start_sms_monitoring(machine, check_interval=check_interval)
            print(f"📱 SMS Monitoring: Enabled (check every {check_interval}s)")
        else:
            print(f"📱 SMS Monitoring: Disabled")
    else:
        print(f"📡 MQTT: Disabled")
    
    print(f"✅ Ready to send/receive SMS messages")

    try:
        if ssl:
            app.run(port=port, host="0.0.0.0", ssl_context=('/ssl/cert.pem', '/ssl/key.pem'),
                    debug=False, use_reloader=False)
        else:
            app.run(port=port, host="0.0.0.0", debug=False, use_reloader=False)
    finally:
        mqtt_publisher.disconnect()