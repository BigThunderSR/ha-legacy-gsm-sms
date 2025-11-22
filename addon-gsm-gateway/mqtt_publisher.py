"""
MQTT Publisher for SMS Gammu Gateway
Publishes SMS and device status to MQTT broker with Home Assistant auto-discovery

Credits:
- Based on PavelVe's SMS Gammu Gateway (https://github.com/PavelVe/home-assistant-addons)
- Original project: pajikos/sms-gammu-gateway (https://github.com/pajikos/sms-gammu-gateway)
- Enhanced with network provider lookup and comprehensive diagnostics by BigThunderSR

Licensed under Apache License 2.0
"""

import json
import time
import logging
import threading
import os
import requests
from typing import Optional, Dict, Any
import paho.mqtt.client as mqtt
import concurrent.futures
from network_codes import get_network_name

logger = logging.getLogger(__name__)

# SMS counter persistence file
SMS_COUNTER_FILE = '/data/sms_counter.json'

def detect_unicode_needed(text: str) -> bool:
    """Detect if text contains non-ASCII characters requiring Unicode encoding"""
    try:
        text.encode('ascii')
        return False
    except UnicodeEncodeError:
        return True

class SMSCounter:
    """Tracks sent SMS count with persistent storage"""

    def __init__(self, counter_file: str = SMS_COUNTER_FILE):
        self.counter_file = counter_file
        self.sent_count = 0
        self._load()

    def _load(self):
        """Load counter from JSON file"""
        try:
            if os.path.exists(self.counter_file):
                with open(self.counter_file, 'r') as f:
                    data = json.load(f)
                    self.sent_count = data.get('sent_count', 0)
                    logger.info(f"📊 Loaded SMS counter from file: {self.sent_count}")
            else:
                logger.info("📊 SMS counter file not found, starting from 0")
        except Exception as e:
            logger.error(f"Error loading SMS counter: {e}")
            self.sent_count = 0

    def _save(self):
        """Save counter to JSON file"""
        try:
            # Ensure /data directory exists
            os.makedirs(os.path.dirname(self.counter_file), exist_ok=True)

            data = {'sent_count': self.sent_count}
            with open(self.counter_file, 'w') as f:
                json.dump(data, f)
            logger.debug(f"📊 Saved SMS counter to file: {self.sent_count}")
        except Exception as e:
            logger.error(f"Error saving SMS counter: {e}")

    def increment(self):
        """Increment counter and save"""
        self.sent_count += 1
        self._save()
        return self.sent_count

    def reset(self):
        """Reset counter to 0"""
        self.sent_count = 0
        self._save()
        logger.info("📊 SMS counter reset to 0")
        return self.sent_count

    def get_count(self):
        """Get current count"""
        return self.sent_count

class SMSHistory:
    """Tracks received SMS history with persistent storage"""

    def __init__(self, history_file='/data/sms_history.json', max_messages=10):
        self.history_file = history_file
        self.max_messages = max_messages
        self.messages = []
        self._load()

    def _load(self):
        """Load history from JSON file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.messages = data.get('messages', [])
                    # Keep only max_messages
                    self.messages = self.messages[-self.max_messages:]
                    logger.info(f"📜 Loaded SMS history: {len(self.messages)} messages")
            else:
                logger.info("📜 SMS history file not found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading SMS history: {e}")
            self.messages = []

    def _save(self):
        """Save history to JSON file"""
        try:
            # Ensure /data directory exists
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

            data = {'messages': self.messages}
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"📜 Saved SMS history: {len(self.messages)} messages")
        except Exception as e:
            logger.error(f"Error saving SMS history: {e}")

    def add_message(self, number, text, timestamp=None):
        """Add a new message to history"""
        if timestamp is None:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        message = {
            "number": number,
            "text": text,  # Store full message text
            "timestamp": timestamp
        }
        
        self.messages.append(message)
        
        # Keep only last max_messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        
        self._save()
        logger.debug(f"📜 Added message to history from {number}")
        return self.messages

    def get_history(self):
        """Get all messages in history"""
        return self.messages

    def clear(self):
        """Clear all history"""
        self.messages = []
        self._save()
        logger.info("📜 SMS history cleared")

class SMSDeliveryTracker:
    """Tracks SMS delivery status and reports"""

    def __init__(self, delivery_file='/data/sms_delivery.json', max_tracked=50):
        self.delivery_file = delivery_file
        self.max_tracked = max_tracked
        self.pending_deliveries = {}  # message_ref -> delivery info
        self._load()

    def _load(self):
        """Load delivery tracking from JSON file"""
        try:
            if os.path.exists(self.delivery_file):
                with open(self.delivery_file, 'r') as f:
                    data = json.load(f)
                    self.pending_deliveries = data.get('pending', {})
                    logger.info(f"📬 Loaded delivery tracking: {len(self.pending_deliveries)} pending")
            else:
                logger.info("📬 Delivery tracking file not found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading delivery tracking: {e}")
            self.pending_deliveries = {}

    def _save(self):
        """Save delivery tracking to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.delivery_file), exist_ok=True)
            
            # Keep only max_tracked most recent entries
            if len(self.pending_deliveries) > self.max_tracked:
                sorted_items = sorted(
                    self.pending_deliveries.items(),
                    key=lambda x: x[1].get('sent_timestamp', ''),
                    reverse=True
                )
                self.pending_deliveries = dict(sorted_items[:self.max_tracked])
            
            data = {'pending': self.pending_deliveries}
            with open(self.delivery_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"📬 Saved delivery tracking: {len(self.pending_deliveries)} pending")
        except Exception as e:
            logger.error(f"Error saving delivery tracking: {e}")

    def track_sent_sms(self, message_ref, number, text_preview):
        """Track a sent SMS awaiting delivery report"""
        if message_ref:
            self.pending_deliveries[str(message_ref)] = {
                "number": number,
                "text_preview": text_preview[:50],  # First 50 chars for identification
                "sent_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "sent"
            }
            self._save()
            logger.info(f"📬 Tracking delivery for message ref {message_ref} to {number}")

    def update_delivery_status(self, message_ref, status, timestamp=None):
        """Update delivery status for a message"""
        ref_str = str(message_ref)
        if ref_str in self.pending_deliveries:
            self.pending_deliveries[ref_str]["status"] = status
            self.pending_deliveries[ref_str]["delivered_timestamp"] = timestamp or time.strftime("%Y-%m-%d %H:%M:%S")
            self._save()
            logger.info(f"📬 Updated delivery status for ref {message_ref}: {status}")
            return self.pending_deliveries[ref_str]
        return None

    def get_pending_count(self):
        """Get count of messages awaiting delivery report"""
        return len([d for d in self.pending_deliveries.values() if d.get('status') == 'sent'])

    def get_all_deliveries(self):
        """Get all tracked deliveries"""
        return self.pending_deliveries

class DeviceConnectivityTracker:
    """Tracks USB GSM device connectivity status based on gammu communication"""

    def __init__(self, offline_timeout_seconds=900):  # 15 minutes default (increased from 10)
        self.last_success_time = None
        self.consecutive_failures = 0
        self.last_error = None
        self.offline_timeout = offline_timeout_seconds
        self.total_operations = 0
        self.successful_operations = 0
        self.initial_check_done = False  # Track if we've done initial modem check
        
    def record_success(self):
        """Record successful gammu operation"""
        self.last_success_time = time.time()

        # Only reset consecutive failures if we had them logged
        if self.consecutive_failures > 0:
            logger.info(f"✅ Device recovery: resetting consecutive_failures from {self.consecutive_failures} to 0")
            self.consecutive_failures = 0

        self.last_error = None
        self.total_operations += 1
        self.successful_operations += 1
        self.initial_check_done = True  # Mark initial check as done on first success
        
    def record_failure(self, error_message=None):
        """Record failed gammu operation"""
        self.consecutive_failures += 1
        self.last_error = str(error_message) if error_message else "Communication failed"
        self.total_operations += 1
        
    def get_status(self):
        """Get current device connectivity status"""
        # If we haven't done initial check yet, assume offline
        if not self.initial_check_done:
            return "offline"

        if self.last_success_time is None:
            return "offline"

        # If we have 2 or more consecutive failures, go offline immediately
        if self.consecutive_failures >= 2:
            return "offline"

        # Check time-based timeout (10 minutes without any communication)
        time_since_last_success = time.time() - self.last_success_time
        if time_since_last_success > self.offline_timeout:
            return "offline"

        # Recent success and < 3 failures = online
        return "online"
            
    def get_status_data(self):
        """Get detailed status information"""
        status = self.get_status()
        
        data = {
            "status": status,
            "consecutive_failures": self.consecutive_failures,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "last_error": self.last_error
        }
        
        if self.last_success_time:
            data["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.last_success_time))
            data["seconds_since_last_success"] = int(time.time() - self.last_success_time)
        else:
            data["last_seen"] = None
            data["seconds_since_last_success"] = None
            
        return data

class MQTTPublisher:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.disconnecting = False  # Flag to prevent multiple disconnect calls
        self.topic_prefix = config.get('mqtt_topic_prefix', 'homeassistant/sensor/sms_gateway')
        self.availability_topic = f"{self.topic_prefix}/availability"  # Shared availability for all entities
        self.gammu_machine = None  # Will be set externally
        self.gammu_lock = threading.Lock()  # Serialize all Gammu operations to prevent race conditions
        self.current_phone_number = ""  # Current phone number from text input
        self.current_message_text = ""  # Current message text from text input
        self.current_ussd_code = ""  # Current USSD code from text input
        self.device_tracker = DeviceConnectivityTracker()  # USB device connectivity tracking
        self.sms_counter = SMSCounter()  # SMS counter with persistence
        
        # Initialize SMS history with configurable max messages (default: 10)
        max_history = config.get('sms_history_max_messages', 10)
        self.sms_history = SMSHistory(max_messages=max_history)  # SMS history with persistence
        
        # Initialize delivery tracking
        self.delivery_tracker = SMSDeliveryTracker()  # SMS delivery report tracking

        if config.get('mqtt_enabled', False):
            self._setup_client()
    
    def set_gammu_machine(self, machine):
        """Set gammu machine for SMS sending"""
        self.gammu_machine = machine
        logger.info("Gammu machine set for MQTT SMS sending")
    
    def _setup_client(self):
        """Setup MQTT client with configuration"""
        try:
            # Create client with unique ID for better connection tracking
            import socket
            client_id = f"sms_gateway_{socket.gethostname()}"
            self.client = mqtt.Client(client_id=client_id, clean_session=True)

            # Set credentials ONLY if username is provided and not empty
            username = self.config.get('mqtt_username', '')
            password = self.config.get('mqtt_password', '')

            # Ensure username is a string and strip whitespace
            if username is None:
                username = ''
            username = str(username).strip()

            # Only set credentials if username has actual content
            if username and username != '':
                self.client.username_pw_set(username, password)
                logger.info(f"MQTT: Client ID: {client_id}, Using authentication with username: '{username}'")
            else:
                logger.info(f"MQTT: Client ID: {client_id}, Connecting without authentication (local broker mode)")
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_publish = self._on_publish
            self.client.on_message = self._on_message

            # Set Last Will and Testament - published if connection lost unexpectedly
            # This makes ALL entities unavailable in HA when addon crashes/stops
            self.client.will_set(self.availability_topic, "offline", qos=1, retain=True)
            logger.info("📡 MQTT Last Will set: all entities will be unavailable if connection lost")

            # Connect to broker
            host = self.config.get('mqtt_host', 'core-mosquitto')
            port = self.config.get('mqtt_port', 1883)

            logger.info(f"Connecting to MQTT broker: {host}:{port}")
            self.client.connect(host, port, 60)
            self.client.loop_start()
            
        except Exception as e:
            logger.error(f"Failed to setup MQTT client: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection"""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker")

            # Publish "online" availability immediately - makes all entities available
            self.client.publish(self.availability_topic, "online", qos=1, retain=True)
            logger.info("📡 Published availability: online")

            self._publish_discovery_configs()
            # Subscribe to SMS send command topic
            send_topic = f"{self.topic_prefix}/send"
            client.subscribe(send_topic)
            logger.info(f"Subscribed to SMS send topic: {send_topic}")

            # Subscribe to SMS button topic
            button_topic = f"{self.topic_prefix}/send_button"
            client.subscribe(button_topic)
            logger.info(f"Subscribed to SMS button topic: {button_topic}")

            # Subscribe to reset counter button
            reset_counter_topic = f"{self.topic_prefix}/reset_counter_button"
            client.subscribe(reset_counter_topic)
            logger.info(f"Subscribed to reset counter topic: {reset_counter_topic}")

            # Subscribe to delete all SMS button
            delete_all_sms_topic = f"{self.topic_prefix}/delete_all_sms_button"
            client.subscribe(delete_all_sms_topic)
            logger.info(f"Subscribed to delete all SMS topic: {delete_all_sms_topic}")

            # Subscribe to text input topics
            phone_topic = f"{self.topic_prefix}/phone_number/set"
            message_topic = f"{self.topic_prefix}/message_text/set"
            phone_state_topic = f"{self.topic_prefix}/phone_number/state"
            message_state_topic = f"{self.topic_prefix}/message_text/state"

            client.subscribe(phone_topic)
            client.subscribe(message_topic)
            client.subscribe(phone_state_topic)  # Subscribe to state topics too
            client.subscribe(message_state_topic)
            logger.info(f"Subscribed to text input topics: {phone_topic}, {message_topic}, {phone_state_topic}, {message_state_topic}")

            # Subscribe to USSD topics
            ussd_code_topic = f"{self.topic_prefix}/ussd_code/set"
            ussd_code_state_topic = f"{self.topic_prefix}/ussd_code/state"
            ussd_button_topic = f"{self.topic_prefix}/send_ussd_button"

            client.subscribe(ussd_code_topic)
            client.subscribe(ussd_code_state_topic)
            client.subscribe(ussd_button_topic)
            logger.info(f"Subscribed to USSD topics: {ussd_code_topic}, {ussd_code_state_topic}, {ussd_button_topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection"""
        self.connected = False
        logger.warning("Disconnected from MQTT broker")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for published messages"""
        pass
    
    def _on_message(self, client, userdata, msg):
        """Callback for received MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.info(f"Received MQTT message on topic {topic}: {payload}")

            # Check message topic and handle accordingly
            send_topic = f"{self.topic_prefix}/send"
            button_topic = f"{self.topic_prefix}/send_button"
            reset_counter_topic = f"{self.topic_prefix}/reset_counter_button"
            delete_all_sms_topic = f"{self.topic_prefix}/delete_all_sms_button"
            phone_topic = f"{self.topic_prefix}/phone_number/set"
            message_topic = f"{self.topic_prefix}/message_text/set"
            phone_state_topic = f"{self.topic_prefix}/phone_number/state"
            message_state_topic = f"{self.topic_prefix}/message_text/state"
            ussd_code_topic = f"{self.topic_prefix}/ussd_code/set"
            ussd_code_state_topic = f"{self.topic_prefix}/ussd_code/state"
            ussd_button_topic = f"{self.topic_prefix}/send_ussd_button"

            if topic == send_topic:
                self._handle_sms_send_command(payload)
            elif topic == button_topic and payload == "PRESS":
                # Button pressed - send SMS using current text inputs
                self._handle_button_sms_send()
            elif topic == reset_counter_topic and payload == "PRESS":
                # Reset counter button pressed
                self._handle_reset_counter()
            elif topic == delete_all_sms_topic and payload == "PRESS":
                # Delete all SMS button pressed
                self._handle_delete_all_sms()
            elif topic == phone_topic:
                # Phone number updated via command topic
                self.current_phone_number = payload
                self._publish_phone_state(payload)
                logger.info(f"Phone number updated via command: {payload}")
            elif topic == message_topic:
                # Message text updated via command topic
                self.current_message_text = payload
                self._publish_message_state(payload)
                logger.info(f"Message text updated via command: {payload}")
            elif topic == phone_state_topic:
                # Phone number state received (sync with HA)
                self.current_phone_number = payload
                logger.info(f"Phone number synced from HA state: {payload}")
            elif topic == message_state_topic:
                # Message text state received (sync with HA)
                self.current_message_text = payload
                logger.info(f"Message text synced from HA state: {payload}")
            elif topic == ussd_code_topic:
                # USSD code updated via command topic
                self.current_ussd_code = payload
                self._publish_ussd_code_state(payload)
                logger.info(f"USSD code updated via command: {payload}")
            elif topic == ussd_code_state_topic:
                # USSD code state received (sync with HA)
                self.current_ussd_code = payload
                logger.info(f"USSD code synced from HA state: {payload}")
            elif topic == ussd_button_topic and payload == "PRESS":
                # USSD button pressed - send USSD using current code
                self._handle_button_ussd_send()

        except Exception as e:
            logger.error(f"Error processing MQTT message on topic {msg.topic}: {e}")
            # Publish error feedback to user via send_status topic
            if self.connected:
                try:
                    status_topic = f"{self.topic_prefix}/send_status"
                    status_data = {
                        "status": "error",
                        "message": f"Command processing failed: {str(e)}",
                        "topic": msg.topic,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    self.client.publish(status_topic, json.dumps(status_data), retain=False)
                except Exception as pub_err:
                    logger.error(f"Failed to publish error status: {pub_err}")
    
    def _handle_sms_send_command(self, payload):
        """Handle SMS send command from MQTT"""
        try:
            # Parse JSON payload
            data = json.loads(payload)
            number = data.get('number')
            text = data.get('text')
            # If 'unicode' is explicitly provided, use it; otherwise use None for auto-detection
            unicode_mode = data.get('unicode') if 'unicode' in data else None

            if not number or not text:
                logger.error("SMS send command missing required fields: number or text")
                return

            logger.info(f"Processing SMS send command: {number} -> {text} (unicode: {unicode_mode if unicode_mode is not None else 'auto'})")

            # Send SMS via gammu machine (will be set externally)
            if hasattr(self, 'gammu_machine') and self.gammu_machine:
                self._send_sms_via_gammu(number, text, unicode_mode)
            else:
                logger.error("Gammu machine not available for SMS sending")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in SMS send command: {e}")
        except Exception as e:
            logger.error(f"Error handling SMS send command: {e}")
    
    def _send_ussd_via_gammu(self, ussd_code):
        """Send USSD code using gammu machine and return response

        Args:
            ussd_code: USSD code to send (e.g., *#123#, *100#)

        Returns:
            str: USSD response text from network
        """
        try:
            logger.info(f"📱 Sending USSD code: {ussd_code}")
            
            # Use DialService to send USSD and get response
            # DialService returns the USSD response as text (or dict with Text key)
            response = self.track_gammu_operation("DialService", self.gammu_machine.DialService, ussd_code)
            
            # Handle response - may be string or dict depending on Gammu version
            if isinstance(response, dict):
                response_text = response.get('Text', str(response))
            else:
                response_text = str(response) if response else "No response"
            
            logger.info(f"✅ USSD Response received: {response_text}")
            
            # Publish USSD response to MQTT
            if self.connected:
                response_topic = f"{self.topic_prefix}/ussd_response/state"
                response_data = {
                    "response": response_text,
                    "code": ussd_code,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self.client.publish(response_topic, json.dumps(response_data), retain=True)
                logger.info(f"📤 Published USSD response to {response_topic}")
            
            return response_text

        except Exception as e:
            error_msg = f"Failed to send USSD code: {str(e)}"
            logger.error(f"❌ {error_msg}")
            
            # Publish error to USSD response sensor
            if self.connected:
                response_topic = f"{self.topic_prefix}/ussd_response/state"
                error_data = {
                    "response": f"ERROR: {str(e)}",
                    "code": ussd_code,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self.client.publish(response_topic, json.dumps(error_data), retain=True)
            
            raise

    def _send_sms_via_gammu(self, number, text, unicode_mode=None):
        """Send SMS using gammu machine

        Args:
            number: Phone number to send to
            text: SMS text content
            unicode_mode: Force unicode mode (True/False), or None for auto-detection
        """
        try:
            # Import gammu and support functions
            from support import encodeSms

            # Auto-detect unicode if not explicitly set
            if unicode_mode is None:
                unicode_mode = detect_unicode_needed(text)
                if unicode_mode:
                    logger.info(f"🔤 Auto-detected non-ASCII characters, using Unicode mode")

            # Prepare SMS info
            smsinfo = {
                "Class": -1,
                "Unicode": unicode_mode,
                "Entries": [
                    {
                        "ID": "ConcatenatedTextLong",
                        "Buffer": text,
                    }
                ],
            }

            # Encode and send SMS
            messages = encodeSms(smsinfo)
            message_refs = []
            for message in messages:
                # Use same SMSC logic as REST API
                config_smsc = self.config.get('smsc_number', '').strip()
                if config_smsc:
                    message["SMSC"] = {'Number': config_smsc}
                    logger.info(f"Using configured SMSC: {config_smsc}")
                else:
                    # Use Location 1 (same as REST API when no SMSC provided)
                    message["SMSC"] = {'Location': 1}
                    logger.info("Using SMSC from Location 1 (same as REST API)")

                message["Number"] = number
                
                # Request delivery report if enabled in config
                if self.config.get('sms_delivery_reports', False):
                    message["DeliveryReport"] = "yes"
                
                result = self.track_gammu_operation("SendSMS", self.gammu_machine.SendSMS, message)
                logger.info(f"SMS sent successfully: {result}")
                
                # Track delivery - result is the message reference
                if result and self.config.get('sms_delivery_reports', False):
                    message_refs.append(result)
                    self.delivery_tracker.track_sent_sms(result, number, text)
                    logger.info(f"📬 Delivery report requested for message ref: {result}")

            # Increment SMS counter and publish
            new_count = self.sms_counter.increment()
            self.publish_sms_counter()
            logger.info(f"📊 SMS counter incremented to: {new_count}")

            # Publish confirmation with message references
            if self.connected:
                status_topic = f"{self.topic_prefix}/send_status"
                status_data = {
                    "status": "success",
                    "number": number,
                    "text": text,
                    "message_refs": message_refs,
                    "pending_delivery_reports": len(message_refs),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self.client.publish(status_topic, json.dumps(status_data), retain=False)
                
                # Publish initial delivery status if enabled
                if self.config.get('sms_delivery_reports', False) and message_refs:
                    self.publish_delivery_pending(message_refs, number)
                
        except Exception as e:
            error_msg = str(e)
            # Try to extract useful error message from gammu error
            if "Code': 27" in error_msg:
                user_error = "SMS sending failed - check SIM card, network signal or device connection"
            elif "Code': 38" in error_msg:
                user_error = "Network registration failed - check SIM card and signal"
            elif "Code': 69" in error_msg:
                user_error = "SMSC number not found - configure SMS center number in SIM settings"
            else:
                user_error = f"SMS sending error: {error_msg}"
            
            logger.error(f"Failed to send SMS via gammu: {error_msg}")
            # Publish error status with user-friendly message
            if self.connected:
                status_topic = f"{self.topic_prefix}/send_status"
                status_data = {
                    "status": "error",
                    "error": user_error,
                    "number": number,
                    "text": text,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self.client.publish(status_topic, json.dumps(status_data), retain=False)
    
    def _handle_button_sms_send(self):
        """Handle SMS send when button is pressed using current text inputs"""
        # Log current state for debugging
        logger.info(f"Button pressed - current state: phone='{self.current_phone_number}', message='{self.current_message_text}'")

        if not self.current_phone_number.strip() or not self.current_message_text.strip():
            # If fields are empty, show instruction
            if self.connected:
                status_topic = f"{self.topic_prefix}/send_status"
                status_data = {
                    "status": "missing_fields",
                    "message": f"Please fill in phone number and message text first. Current: phone='{self.current_phone_number}', message='{self.current_message_text}'",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self.client.publish(status_topic, json.dumps(status_data), retain=False)
            logger.warning(f"Button pressed but fields empty: phone='{self.current_phone_number}', message='{self.current_message_text}'")
            return

        # Send SMS using current values
        logger.info(f"Button SMS send: {self.current_phone_number} -> {self.current_message_text}")
        if hasattr(self, 'gammu_machine') and self.gammu_machine:
            # Use unicode_mode=None for auto-detection
            self._send_sms_via_gammu(self.current_phone_number, self.current_message_text, unicode_mode=None)
            # Always clear fields after send attempt (success or failure)
            self._clear_text_fields()
        else:
            logger.error("Gammu machine not available for SMS sending")
            # Clear fields even if gammu not available
            self._clear_text_fields()

    def _handle_button_ussd_send(self):
        """Handle USSD send when button is pressed using current USSD code"""
        logger.info(f"USSD button pressed - current code: '{self.current_ussd_code}'")

        if not self.current_ussd_code.strip():
            # If USSD code is empty, show instruction
            if self.connected:
                response_topic = f"{self.topic_prefix}/ussd_response/state"
                response_data = {
                    "response": "ERROR: Please enter a USSD code first (e.g., *#100#)",
                    "code": "",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self.client.publish(response_topic, json.dumps(response_data), retain=True)
            logger.warning(f"USSD button pressed but code field is empty")
            return

        # Send USSD using current value
        logger.info(f"Sending USSD code: {self.current_ussd_code}")
        if hasattr(self, 'gammu_machine') and self.gammu_machine:
            try:
                response = self._send_ussd_via_gammu(self.current_ussd_code)
                logger.info(f"✅ USSD sent successfully, response: {response}")
                # Clear USSD code after successful send
                self.current_ussd_code = ""
                self._publish_ussd_code_state("")
            except Exception as e:
                logger.error(f"❌ USSD send failed: {e}")
        else:
            logger.error("Gammu machine not available for USSD sending")
    
    def _handle_reset_counter(self):
        """Handle reset counter button press"""
        logger.info("🔄 Reset counter button pressed")
        self.sms_counter.reset()
        self.publish_sms_counter()
        logger.info("✅ SMS counter reset to 0")

    def _handle_delete_all_sms(self):
        """Handle delete all SMS button press - with fallback for corrupted SMS"""
        logger.info("🗑️ Delete all SMS button pressed")
        try:
            if hasattr(self, 'gammu_machine') and self.gammu_machine:
                from support import retrieveAllSms, deleteSms

                deleted_count = 0

                # Try method 1: Retrieve and delete SMS one by one
                try:
                    all_sms = self.track_gammu_operation("retrieveAllSms", retrieveAllSms, self.gammu_machine)
                    count = len(all_sms)

                    logger.info(f"📋 Found {count} SMS to delete")

                    # Delete each SMS
                    for sms in all_sms:
                        try:
                            self.track_gammu_operation("deleteSms", deleteSms, self.gammu_machine, sms)
                            deleted_count += 1
                        except Exception as e:
                            logger.warning(f"Could not delete SMS at location {sms.get('Location', 'unknown')}: {e}")

                    logger.info(f"✅ Method 1: Deleted {deleted_count}/{count} SMS messages")

                except Exception as e:
                    # Method 1 failed (likely corrupted SMS) - try method 2
                    logger.warning(f"⚠️ Method 1 failed (corrupted SMS?): {e}")
                    logger.info("🔄 Trying Method 2: Delete by location numbers...")

                    # Method 2: Get SMS capacity and delete by location
                    try:
                        capacity = self.track_gammu_operation("GetSMSStatus", self.gammu_machine.GetSMSStatus)
                        sim_size = capacity.get('SIMSize', 50)  # Default 50 if unknown

                        logger.info(f"📋 Attempting to delete SMS from {sim_size} locations")

                        # Try to delete each location (even corrupted ones)
                        # Use multiple folder IDs to catch SMS in different folders
                        for location in range(1, sim_size + 1):
                            deleted_this_location = False

                            # Try different folder IDs (0=Inbox, 1=Outbox, 2=Sent, etc.)
                            for folder in [0, 1, 2]:
                                try:
                                    self.gammu_machine.DeleteSMS(folder, location)
                                    deleted_count += 1
                                    deleted_this_location = True
                                    logger.info(f"✅ Deleted SMS at folder={folder}, location={location}")
                                    break  # Success - don't try other folders for this location
                                except Exception as loc_err:
                                    error_msg = str(loc_err)
                                    # Only log if it's not just "empty location"
                                    if "Empty" not in error_msg and "InvalidLocation" not in error_msg:
                                        logger.debug(f"Folder {folder}, Location {location}: {error_msg}")

                            if not deleted_this_location:
                                logger.debug(f"Location {location}: no SMS found in any folder")

                        logger.info(f"✅ Method 2: Processed {sim_size} locations, deleted {deleted_count} SMS")

                    except Exception as capacity_err:
                        logger.error(f"Method 2 also failed: {capacity_err}")
                        raise Exception(f"Both deletion methods failed. Last error: {capacity_err}")

                # Give modem time to process bulk deletion (prevents Code 27 errors)
                if deleted_count > 0:
                    logger.info("⏳ Waiting for modem to stabilize after bulk deletion...")
                    time.sleep(3)  # 3 second pause

                # Update SMS capacity after deletion
                try:
                    capacity = self.track_gammu_operation("GetSMSStatus", self.gammu_machine.GetSMSStatus)
                    self.publish_sms_capacity(capacity)
                    logger.info(f"📊 Updated SMS capacity: {capacity.get('SIMUsed', 0)}/{capacity.get('SIMSize', 0)}")
                except Exception as e:
                    logger.warning(f"Could not update SMS capacity: {e}")

                # Publish success status to MQTT
                if self.connected:
                    status_topic = f"{self.topic_prefix}/delete_sms_status"
                    status_data = {
                        "status": "success",
                        "deleted_count": deleted_count,
                        "message": f"Deleted {deleted_count} SMS messages from SIM",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                    self.client.publish(status_topic, json.dumps(status_data), retain=False)
            else:
                logger.error("Gammu machine not available for deleting SMS")
        except Exception as e:
            logger.error(f"Error deleting all SMS: {e}")
            if self.connected:
                status_topic = f"{self.topic_prefix}/delete_sms_status"
                status_data = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                self.client.publish(status_topic, json.dumps(status_data), retain=False)

    def _clear_text_fields(self):
        """Clear both phone and message fields after sending SMS"""
        # Clear both fields
        self.current_phone_number = ""
        self.current_message_text = ""

        # Try to clear both fields in UI if connected
        if self.connected and self.client:
            try:
                phone_state_topic = f"{self.topic_prefix}/phone_number/state"
                message_state_topic = f"{self.topic_prefix}/message_text/state"

                # Clear both fields with retain=True
                self.client.publish(phone_state_topic, "", retain=True, qos=1)
                self.client.publish(message_state_topic, "", retain=True, qos=1)

                logger.info("🧹 Cleared both phone and message text fields after sending SMS")
            except Exception as e:
                logger.warning(f"Could not clear text fields in UI: {e}")
        else:
            logger.info("🧹 Cleared both text fields (internal state only)")
    
    def _publish_phone_state(self, value):
        """Publish phone number state"""
        if self.connected:
            state_topic = f"{self.topic_prefix}/phone_number/state"
            self.client.publish(state_topic, value, retain=True, qos=1)

    def _publish_message_state(self, value):
        """Publish message text state"""
        if self.connected:
            state_topic = f"{self.topic_prefix}/message_text/state"
            self.client.publish(state_topic, value, retain=True, qos=1)

    def _publish_ussd_code_state(self, value):
        """Publish USSD code state"""
        if self.connected:
            state_topic = f"{self.topic_prefix}/ussd_code/state"
            self.client.publish(state_topic, value, retain=True, qos=1)
    
    def _publish_discovery_configs(self):
        """Publish Home Assistant auto-discovery configurations"""
        if not self.connected:
            return

        # Common device config for all entities
        DEVICE_CONFIG = {
            "identifiers": ["sms_gateway"],
            "name": "SMS Gateway",
            "model": "GSM Modem",
            "manufacturer": "Gammu Gateway"
        }

        # Common availability config - all entities share same availability topic
        AVAILABILITY_CONFIG = {
            "availability_topic": self.availability_topic,
            "payload_available": "online",
            "payload_not_available": "offline"
        }

        # Signal strength sensor (original from PavelVe)
        signal_config = {
            "name": "GSM Signal Strength",
            "unique_id": "sms_gateway_signal",
            "state_topic": f"{self.topic_prefix}/signal/state",
            "value_template": "{{ value_json.SignalPercent }}",
            "unit_of_measurement": "%",
            "icon": "mdi:signal-cellular-3",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }
        
        # Signal strength dBm sensor (diagnostic - shows actual dBm value, not percent)
        signal_dbm_config = {
            "name": "GSM Signal Strength",
            "unique_id": "sms_gateway_signal_dbm",
            "state_topic": f"{self.topic_prefix}/signal/state",
            "value_template": "{{ value_json.SignalStrength }}",
            "unit_of_measurement": "dBm",
            "device_class": "signal_strength",
            "entity_category": "diagnostic",
            "icon": "mdi:signal",
            "state_class": "measurement",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }
        
        # Bit Error Rate sensor (diagnostic)
        ber_config = {
            "name": "GSM Bit Error Rate",
            "unique_id": "sms_gateway_ber",
            "state_topic": f"{self.topic_prefix}/signal/state",
            "value_template": "{{ value_json.BitErrorRate }}",
            "unit_of_measurement": "%",
            "entity_category": "diagnostic",
            "icon": "mdi:gauge",
            "state_class": "measurement",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }
        
        # Network info sensor (original from PavelVe)
        network_config = {
            "name": "GSM Network",
            "unique_id": "sms_gateway_network",
            "state_topic": f"{self.topic_prefix}/network/state",
            "value_template": "{{ value_json.NetworkName }}",
            "icon": "mdi:network",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }
        
        # Network registration state sensor (main display)
        network_state_config = {
            "name": "GSM Network State",
            "unique_id": "sms_gateway_network_state",
            "state_topic": f"{self.topic_prefix}/network/state",
            "value_template": "{{ value_json.State }}",
            "icon": "mdi:signal-variant",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }
        
        # Network code (MCC+MNC) sensor (diagnostic)
        network_code_config = {
            "name": "GSM Network Code",
            "unique_id": "sms_gateway_network_code",
            "state_topic": f"{self.topic_prefix}/network/state",
            "value_template": "{{ value_json.NetworkCode }}",
            "icon": "mdi:network",
            "entity_category": "diagnostic",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }
        
        # Cell ID sensor
        cid_config = {
            "name": "GSM Cell ID",
            "unique_id": "sms_gateway_cid",
            "state_topic": f"{self.topic_prefix}/network/state",
            "value_template": "{{ value_json.CID }}",
            "icon": "mdi:radio-tower",
            "entity_category": "diagnostic",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }
        
        # Location Area Code sensor
        lac_config = {
            "name": "GSM Location Area Code",
            "unique_id": "sms_gateway_lac",
            "state_topic": f"{self.topic_prefix}/network/state",
            "value_template": "{{ value_json.LAC }}",
            "icon": "mdi:map-marker-radius",
            "entity_category": "diagnostic",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # Last SMS sensor
        sms_config = {
            "name": "Last SMS Received",
            "unique_id": "sms_gateway_last_sms",
            "state_topic": f"{self.topic_prefix}/sms/state",
            "value_template": "{{ value_json.Text }}",
            "json_attributes_topic": f"{self.topic_prefix}/sms/state",
            "json_attributes_template": "{{ {'Number': value_json.Number, 'timestamp': value_json.timestamp, 'history': value_json.history} | tojson }}",
            "icon": "mdi:message-text",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # Last SMS sender number sensor
        sms_sender_config = {
            "name": "Last SMS Sender",
            "unique_id": "sms_gateway_last_sms_sender",
            "state_topic": f"{self.topic_prefix}/sms/state",
            "value_template": "{{ value_json.Number }}",
            "icon": "mdi:phone",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # SMS send status sensor
        send_status_config = {
            "name": "SMS Send Status",
            "unique_id": "sms_gateway_send_status",
            "state_topic": f"{self.topic_prefix}/send_status",
            "value_template": "{{ value_json.status }}",
            "json_attributes_topic": f"{self.topic_prefix}/send_status",
            "icon": "mdi:send",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # SMS delete status sensor
        delete_status_config = {
            "name": "SMS Delete Status",
            "unique_id": "sms_gateway_delete_status",
            "state_topic": f"{self.topic_prefix}/delete_sms_status",
            "value_template": "{{ value_json.status }}",
            "json_attributes_topic": f"{self.topic_prefix}/delete_sms_status",
            "icon": "mdi:delete-sweep",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # SMS delivery report sensor (🆕 v2.1.0)
        delivery_report_config = {
            "name": "SMS Delivery Status",
            "unique_id": "sms_gateway_delivery_status",
            "state_topic": f"{self.topic_prefix}/delivery_status",
            "value_template": "{{ value_json.status }}",
            "json_attributes_topic": f"{self.topic_prefix}/delivery_status",
            "icon": "mdi:email-check",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # SMS send button
        button_config = {
            "name": "Send SMS",
            "unique_id": "sms_gateway_send_button",
            "command_topic": f"{self.topic_prefix}/send_button",
            "payload_press": "PRESS",
            "icon": "mdi:message-plus",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # Phone number input text
        phone_text_config = {
            "name": "Phone Number",
            "unique_id": "sms_gateway_phone_number",
            "command_topic": f"{self.topic_prefix}/phone_number/set",
            "state_topic": f"{self.topic_prefix}/phone_number/state",
            "icon": "mdi:phone",
            "mode": "text",
            "pattern": r"^\+?[\d\s\-\(\)]*$",  # Allow empty string with *
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # Message input text
        message_text_config = {
            "name": "Message Text",
            "unique_id": "sms_gateway_message_text",
            "command_topic": f"{self.topic_prefix}/message_text/set",
            "state_topic": f"{self.topic_prefix}/message_text/state",
            "icon": "mdi:message-text",
            "mode": "text",
            "max": 255,  # HA text entity max length (Gammu will still split long messages into multiple SMS)
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # USSD code input text
        ussd_code_text_config = {
            "name": "USSD Code",
            "unique_id": "sms_gateway_ussd_code",
            "command_topic": f"{self.topic_prefix}/ussd_code/set",
            "state_topic": f"{self.topic_prefix}/ussd_code/state",
            "icon": "mdi:pound",
            "mode": "text",
            "pattern": r"^\*[0-9#\*]+#?$",  # USSD codes start with * followed by digits/# (e.g., *225#, *#100#)
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # USSD send button
        ussd_button_config = {
            "name": "Send USSD",
            "unique_id": "sms_gateway_send_ussd_button",
            "command_topic": f"{self.topic_prefix}/send_ussd_button",
            "payload_press": "PRESS",
            "icon": "mdi:dialpad",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # USSD response sensor
        ussd_response_config = {
            "name": "USSD Response",
            "unique_id": "sms_gateway_ussd_response",
            "state_topic": f"{self.topic_prefix}/ussd_response/state",
            "value_template": "{{ value_json.response }}",
            "json_attributes_topic": f"{self.topic_prefix}/ussd_response/state",
            "icon": "mdi:message-reply-text",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # Modem Status sensor
        device_status_config = {
            "name": "Modem Status",
            "unique_id": "sms_gateway_modem_status",
            "state_topic": f"{self.topic_prefix}/device_status/state",
            "value_template": "{{ value_json.status }}",
            "json_attributes_topic": f"{self.topic_prefix}/device_status/state",
            "icon": "mdi:connection",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # SMS Counter sensor
        sms_counter_config = {
            "name": "SMS Sent Count",
            "unique_id": "sms_gateway_sent_count",
            "state_topic": f"{self.topic_prefix}/sms_counter/state",
            "value_template": "{{ value_json.count }}",
            "icon": "mdi:counter",
            "state_class": "total_increasing",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # SMS Cost sensor (only if cost > 0)
        sms_cost_per_message = self.config.get('sms_cost_per_message', 0.0)

        # Reset counter button
        reset_counter_button_config = {
            "name": "Reset SMS Counter",
            "unique_id": "sms_gateway_reset_counter",
            "command_topic": f"{self.topic_prefix}/reset_counter_button",
            "payload_press": "PRESS",
            "icon": "mdi:restart",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # Delete all SMS button
        delete_all_sms_button_config = {
            "name": "Delete All SMS",
            "unique_id": "sms_gateway_delete_all_sms",
            "command_topic": f"{self.topic_prefix}/delete_all_sms_button",
            "payload_press": "PRESS",
            "icon": "mdi:delete-sweep",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # Modem IMEI sensor
        modem_imei_config = {
            "name": "Modem IMEI",
            "unique_id": "sms_gateway_modem_imei",
            "state_topic": f"{self.topic_prefix}/modem_info/state",
            "value_template": "{{ value_json.IMEI }}",
            "icon": "mdi:identifier",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # Modem Model sensor
        modem_model_config = {
            "name": "Modem Model",
            "unique_id": "sms_gateway_modem_model",
            "state_topic": f"{self.topic_prefix}/modem_info/state",
            "value_template": "{{ value_json.Manufacturer }} {{ value_json.Model }}",
            "icon": "mdi:cellphone",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # SIM IMSI sensor
        sim_imsi_config = {
            "name": "SIM IMSI",
            "unique_id": "sms_gateway_sim_imsi",
            "state_topic": f"{self.topic_prefix}/sim_info/state",
            "value_template": "{{ value_json.IMSI }}",
            "icon": "mdi:sim",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # SMS Capacity sensor
        sms_capacity_config = {
            "name": "SMS Storage Used",
            "unique_id": "sms_gateway_sms_capacity",
            "state_topic": f"{self.topic_prefix}/sms_capacity/state",
            "value_template": "{{ value_json.SIMUsed }}",
            "json_attributes_topic": f"{self.topic_prefix}/sms_capacity/state",
            "unit_of_measurement": "messages",
            "icon": "mdi:email-multiple",
            "device": DEVICE_CONFIG,
            **AVAILABILITY_CONFIG
        }

        # Publish discovery configs - all using consistent node_id "sms_gateway" for proper grouping
        discoveries = [
            # Signal sensors
            ("homeassistant/sensor/sms_gateway/signal/config", signal_config),
            ("homeassistant/sensor/sms_gateway/signal_dbm/config", signal_dbm_config),
            ("homeassistant/sensor/sms_gateway/ber/config", ber_config),
            # Network sensors
            ("homeassistant/sensor/sms_gateway/network/config", network_config),
            ("homeassistant/sensor/sms_gateway/network_state/config", network_state_config),
            ("homeassistant/sensor/sms_gateway/network_code/config", network_code_config),
            ("homeassistant/sensor/sms_gateway/cid/config", cid_config),
            ("homeassistant/sensor/sms_gateway/lac/config", lac_config),
            # SMS sensors
            ("homeassistant/sensor/sms_gateway/last_sms/config", sms_config),
            ("homeassistant/sensor/sms_gateway/last_sms_sender/config", sms_sender_config),
            ("homeassistant/sensor/sms_gateway/send_status/config", send_status_config),
            ("homeassistant/sensor/sms_gateway/delete_status/config", delete_status_config),
            ("homeassistant/sensor/sms_gateway/delivery_status/config", delivery_report_config),
            ("homeassistant/sensor/sms_gateway/sent_count/config", sms_counter_config),
            ("homeassistant/sensor/sms_gateway/sms_capacity/config", sms_capacity_config),
            # Modem/SIM sensors
            ("homeassistant/sensor/sms_gateway/modem_status/config", device_status_config),
            ("homeassistant/sensor/sms_gateway/modem_imei/config", modem_imei_config),
            ("homeassistant/sensor/sms_gateway/modem_model/config", modem_model_config),
            ("homeassistant/sensor/sms_gateway/sim_imsi/config", sim_imsi_config),
            # Controls
            ("homeassistant/button/sms_gateway/send_button/config", button_config),
            ("homeassistant/button/sms_gateway/reset_counter/config", reset_counter_button_config),
            ("homeassistant/button/sms_gateway/delete_all_sms/config", delete_all_sms_button_config),
            ("homeassistant/button/sms_gateway/send_ussd_button/config", ussd_button_config),
            ("homeassistant/text/sms_gateway/phone_number/config", phone_text_config),
            ("homeassistant/text/sms_gateway/message_text/config", message_text_config),
            ("homeassistant/text/sms_gateway/ussd_code/config", ussd_code_text_config),
            # USSD response sensor
            ("homeassistant/sensor/sms_gateway/ussd_response/config", ussd_response_config)
        ]

        # Add cost sensor only if cost is configured (> 0)
        if sms_cost_per_message > 0:
            sms_cost_currency = self.config.get('sms_cost_currency', 'CZK')
            sms_cost_config = {
                "name": "SMS Total Cost",
                "unique_id": "sms_gateway_total_cost",
                "state_topic": f"{self.topic_prefix}/sms_counter/state",
                "value_template": "{{ value_json.cost }}",
                "icon": "mdi:cash",
                "unit_of_measurement": sms_cost_currency,
                "state_class": "total",
                "device": DEVICE_CONFIG,
                **AVAILABILITY_CONFIG
            }
            discoveries.append(("homeassistant/sensor/sms_gateway/total_cost/config", sms_cost_config))
        
        for topic, config in discoveries:
            self.client.publish(topic, json.dumps(config), retain=True, qos=1)
        
        logger.info("Published MQTT discovery configurations including SMS send button")
        
        # Publish initial states immediately after discovery
        self._publish_initial_states()

        # Give HA a moment to process discovery and send retained state messages back to us
        import time
        time.sleep(1)
    
    def publish_signal_strength(self, signal_data: Dict[str, Any]):
        """Publish signal strength data"""
        if not self.connected:
            return
            
        topic = f"{self.topic_prefix}/signal/state"
        self.client.publish(topic, json.dumps(signal_data), retain=True)
        logger.info(f"📡 Published signal strength to MQTT: {signal_data.get('SignalPercent', 'N/A')}%")
    
    def publish_network_info(self, network_data: Dict[str, Any]):
        """Publish network information"""
        if not self.connected:
            return
            
        topic = f"{self.topic_prefix}/network/state"
        self.client.publish(topic, json.dumps(network_data), retain=True)
        logger.info(f"📡 Published network info to MQTT: {network_data.get('NetworkName', 'Unknown')}")
    
    def publish_sms_received(self, sms_data: Dict[str, Any]):
        """Publish received SMS data and fire Home Assistant event"""
        if not self.connected:
            return
            
        # Add timestamp
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        sms_data['timestamp'] = timestamp
        
        # Add message to history
        self.sms_history.add_message(
            number=sms_data.get('Number', 'Unknown'),
            text=sms_data.get('Text', ''),
            timestamp=timestamp
        )
        
        # Include history in published data
        sms_data['history'] = self.sms_history.get_history()
        
        topic = f"{self.topic_prefix}/sms/state"
        self.client.publish(topic, json.dumps(sms_data), qos=1)
        
        # Fire Home Assistant event for reliable automation triggering
        self.fire_ha_event(sms_data)
        
        logger.info(f"📡 Published SMS to MQTT: {sms_data.get('Number', 'Unknown')} -> {sms_data.get('Text', '')}")
    
    def fire_ha_event(self, sms_data: Dict[str, Any]):
        """Fire a Home Assistant event for received SMS using HTTP API"""
        # Prepare event data - field names match deprecated legacy_gsm_sms integration
        # for backwards compatibility: phone, text, date (+ timestamp, state for extra info)
        event_data = {
            "phone": sms_data.get('Number', 'Unknown'),  # Matches deprecated integration
            "text": sms_data.get('Text', ''),            # Matches deprecated integration
            "date": sms_data.get('Date', ''),            # Matches deprecated integration
            "timestamp": sms_data.get('timestamp', ''),  # Additional field for unix timestamp
            "state": sms_data.get('State', 'UnRead')     # Additional field for SMS state
        }
        
        logger.info(f"🔔 Attempting to fire HA event for SMS from {event_data['phone']}")
        
        try:
            # Use Home Assistant API - requires homeassistant_api: true in config.yaml
            ha_token = os.environ.get('SUPERVISOR_TOKEN', '')
            if not ha_token:
                logger.error("❌ No SUPERVISOR_TOKEN found - cannot fire HA event")
                return
            
            # Use supervisor proxy to HA Core API (same as standalone addon)
            ha_url = "http://supervisor/core/api"
            url = f"{ha_url}/events/sms_gateway_message_received"
            headers = {
                'Authorization': f'Bearer {ha_token}',
                'Content-Type': 'application/json'
            }
            
            logger.debug(f"Posting to {url} with token length: {len(ha_token)}")
            response = requests.post(url, headers=headers, json=event_data, timeout=5)
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ Successfully fired Home Assistant event: sms_gateway_message_received from {event_data['phone']}")
            else:
                logger.error(f"❌ Failed to fire HA event: HTTP {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error firing HA event: {e}")
        except Exception as e:
            logger.error(f"❌ Unexpected error firing HA event: {e}", exc_info=True)
    
    def publish_device_status(self):
        """Publish USB device connectivity status"""
        status_data = self.device_tracker.get_status_data()
        status = status_data.get('status')

        # Always log status changes, even if MQTT is disconnected
        if hasattr(self, '_last_device_status') and self._last_device_status != status:
            if status == 'online':
                logger.info(f"📶 Modem: ONLINE (after {status_data.get('consecutive_failures', 0)} failures)")
            elif status == 'offline':
                logger.warning(f"❌ Modem: OFFLINE (no response for {status_data.get('seconds_since_last_success', 0)}s)")
            elif status == 'unknown':
                logger.info("❓ Modem: UNKNOWN (no communication attempts yet)")

        self._last_device_status = status

        # Skip MQTT publish if status data hasn't changed (optimization)
        if hasattr(self, '_last_published_status_data') and self._last_published_status_data == status_data:
            logger.debug("Device status data unchanged, skipping redundant MQTT publish")
            return

        # Publish to MQTT if connected
        if self.connected:
            topic = f"{self.topic_prefix}/device_status/state"
            self.client.publish(topic, json.dumps(status_data), retain=True, qos=1)
            self._last_published_status_data = status_data.copy()  # Cache published data
            logger.debug(f"📡 Published device status to MQTT: {status}")
        else:
            logger.debug("Device status changed but MQTT not connected, skipping publish")

    def publish_sms_counter(self):
        """Publish SMS counter and cost data"""
        if not self.connected:
            return

        count = self.sms_counter.get_count()
        sms_cost_per_message = self.config.get('sms_cost_per_message', 0.0)
        total_cost = count * sms_cost_per_message

        counter_data = {
            "count": count,
            "cost": round(total_cost, 2)
        }

        topic = f"{self.topic_prefix}/sms_counter/state"
        self.client.publish(topic, json.dumps(counter_data), retain=True)
        logger.debug(f"📊 Published SMS counter: {count}, cost: {total_cost}")

    def publish_modem_info(self, modem_data: Dict[str, Any]):
        """Publish modem hardware information"""
        if not self.connected:
            return

        topic = f"{self.topic_prefix}/modem_info/state"
        self.client.publish(topic, json.dumps(modem_data), retain=True)
        logger.info(f"📡 Published modem info to MQTT: {modem_data.get('Manufacturer', 'Unknown')} {modem_data.get('Model', 'Unknown')}")

    def publish_sim_info(self, sim_data: Dict[str, Any]):
        """Publish SIM card information"""
        if not self.connected:
            return

        topic = f"{self.topic_prefix}/sim_info/state"
        self.client.publish(topic, json.dumps(sim_data), retain=True)
        logger.info(f"📡 Published SIM info to MQTT: IMSI={sim_data.get('IMSI', 'Unknown')}")

    def publish_sms_capacity(self, capacity_data: Dict[str, Any]):
        """Publish SMS storage capacity"""
        if not self.connected:
            return

        topic = f"{self.topic_prefix}/sms_capacity/state"
        self.client.publish(topic, json.dumps(capacity_data), retain=True)
        logger.info(f"📡 Published SMS capacity to MQTT: {capacity_data.get('SIMUsed', 0)}/{capacity_data.get('SIMSize', 0)}")
    
    def publish_delivery_pending(self, message_refs, number):
        """Publish pending delivery status"""
        if not self.connected or not message_refs:
            return
        
        topic = f"{self.topic_prefix}/delivery_status"
        status_data = {
            "status": "pending",
            "message_refs": message_refs,
            "number": number,
            "pending_count": self.delivery_tracker.get_pending_count(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.client.publish(topic, json.dumps(status_data), retain=True)
        logger.info(f"📬 Published pending delivery status for {len(message_refs)} message(s) to {number}")
    
    def publish_delivery_report(self, message_ref, status, delivery_info):
        """Publish delivery report when received"""
        if not self.connected:
            return
        
        topic = f"{self.topic_prefix}/delivery_status"
        status_data = {
            "status": status,
            "message_ref": message_ref,
            "number": delivery_info.get("number", "Unknown"),
            "text_preview": delivery_info.get("text_preview", ""),
            "sent_timestamp": delivery_info.get("sent_timestamp", ""),
            "delivered_timestamp": delivery_info.get("delivered_timestamp", ""),
            "pending_count": self.delivery_tracker.get_pending_count(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.client.publish(topic, json.dumps(status_data), retain=True)
        logger.info(f"📬 Published delivery report: ref={message_ref}, status={status}")
        
    def track_gammu_operation(self, operation_name, gammu_function, *args, **kwargs):
        """Execute gammu operation with connectivity tracking, thread safety, and Python-level timeout"""
        # Use lock to serialize all Gammu operations (prevent race conditions on serial port)
        with self.gammu_lock:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(gammu_function, *args, **kwargs)
                try:
                    # Python-level timeout (15s) as second defense layer
                    # Primary defense is Gammu commtimeout=10s in config
                    result = future.result(timeout=15)
                    self.device_tracker.record_success()
                    self.publish_device_status()
                    logger.debug(f"✅ Gammu operation '{operation_name}' succeeded")

                    # Small delay after each operation to let modem "breathe"
                    # Prevents buffer overflow on modems like Huawei E1750
                    time.sleep(0.3)

                    return result
                except concurrent.futures.TimeoutError:
                    # Operation timed out at Python level
                    self.device_tracker.record_failure(f"{operation_name}: Python timeout (15s)")
                    self.publish_device_status()
                    logger.error(f"⏱️ Gammu operation '{operation_name}' timed out after 15s")
                    raise TimeoutError(f"Gammu operation '{operation_name}' timed out after 15s")
                except Exception as e:
                    # All other errors (including Gammu commtimeout errors)
                    self.device_tracker.record_failure(f"{operation_name}: {str(e)}")
                    self.publish_device_status()
                    raise
    
    def _publish_initial_states(self):
        """Publish initial sensor states on startup"""
        if self.connected:
            # Reset both text input fields on startup (clear any old values from broker)
            phone_state_topic = f"{self.topic_prefix}/phone_number/state"
            message_state_topic = f"{self.topic_prefix}/message_text/state"

            # First, delete old retained messages by publishing null payload
            self.client.publish(phone_state_topic, None, retain=True, qos=1)
            self.client.publish(message_state_topic, None, retain=True, qos=1)

            # Small delay to ensure deletion is processed
            import time
            time.sleep(0.1)

            # Now publish empty string as initial value (creates entity in HA)
            self.client.publish(phone_state_topic, "", retain=True, qos=1)
            self.client.publish(message_state_topic, "", retain=True, qos=1)

            # Reset internal state
            self.current_phone_number = ""
            self.current_message_text = ""

            logger.info("📡 Published initial text field states: cleared both phone and message fields")

            # Publish initial send_status as "ready"
            send_status_topic = f"{self.topic_prefix}/send_status"
            send_status_data = {
                "status": "ready",
                "message": "SMS Gateway ready to send messages",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.client.publish(send_status_topic, json.dumps(send_status_data), retain=False)

            # Publish initial delete_status as "idle"
            delete_status_topic = f"{self.topic_prefix}/delete_sms_status"
            delete_status_data = {
                "status": "idle",
                "message": "No delete operations yet",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.client.publish(delete_status_topic, json.dumps(delete_status_data), retain=False)

            logger.info("📡 Published initial status states (send_status: ready, delete_status: idle)")
    
    def publish_initial_states_with_machine(self, gammu_machine):
        """Publish initial states with gammu machine access"""
        if not self.connected:
            logger.info("📡 MQTT not connected, skipping initial state publish")
            return

        try:
            from gammu import GSMNetworks

            # Publish initial offline status (will change to online on first successful operation)
            self.publish_device_status()
            logger.info("📡 Published initial modem status: offline (waiting for first successful communication)")

            # Publish initial signal strength with connectivity tracking
            signal = self.track_gammu_operation("GetSignalQuality", gammu_machine.GetSignalQuality)
            # Filter out invalid BER value (-1 means not available)
            if signal.get("BitErrorRate") == -1:
                signal["BitErrorRate"] = None
            self.publish_signal_strength(signal)

            # Publish initial network info with connectivity tracking
            network = self.track_gammu_operation("GetNetworkInfo", gammu_machine.GetNetworkInfo)
            network_code = network.get("NetworkCode", "")
            network_name = network.get("NetworkName")
            
            # Try multiple lookup methods if name is empty (Gammu bug: https://github.com/gammu/python-gammu/issues/31)
            if not network_name and network_code:
                # First try our comprehensive database
                network_name = get_network_name(network_code)
                # Fallback to Gammu's database
                if not network_name:
                    network_name = GSMNetworks.get(network_code, 'Unknown')
            
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
            
            self.publish_network_info(network)

            # Don't publish empty SMS state on startup - it would overwrite the last real SMS
            # The SMS state will be updated when:
            # 1. A new SMS arrives (SMS monitoring)
            # 2. User retrieves SMS via API
            # This preserves the last SMS value across restarts
            logger.info("📡 Skipping empty SMS state publish (preserves last SMS across restarts)")

            # Publish initial SMS counter
            self.publish_sms_counter()

            # Publish modem info
            try:
                modem_info = {
                    "IMEI": self.track_gammu_operation("GetIMEI", gammu_machine.GetIMEI),
                    "Manufacturer": self.track_gammu_operation("GetManufacturer", gammu_machine.GetManufacturer),
                    "Model": self.track_gammu_operation("GetModel", gammu_machine.GetModel)
                }
                try:
                    modem_info["Firmware"] = self.track_gammu_operation("GetFirmware", gammu_machine.GetFirmware)[0]
                except Exception:
                    modem_info["Firmware"] = "Unknown"
                self.publish_modem_info(modem_info)
            except Exception as e:
                logger.warning(f"Could not publish modem info: {e}")

            # Publish SIM info
            try:
                sim_info = {"IMSI": self.track_gammu_operation("GetSIMIMSI", gammu_machine.GetSIMIMSI)}
                self.publish_sim_info(sim_info)
            except Exception as e:
                logger.warning(f"Could not publish SIM info: {e}")

            # Publish SMS capacity
            try:
                capacity = self.track_gammu_operation("GetSMSStatus", gammu_machine.GetSMSStatus)
                self.publish_sms_capacity(capacity)
            except Exception as e:
                logger.warning(f"Could not publish SMS capacity: {e}")

            logger.info("📡 Published initial states to MQTT")

        except Exception as e:
            logger.error(f"Error publishing initial states: {e}")
    
    def start_sms_monitoring(self, gammu_machine, check_interval=10):
        """Start SMS monitoring in background thread"""
        if not self.connected:
            return
            
        def _sms_monitor_loop():
            logger.info(f"📱 Started SMS monitoring (check every {check_interval}s)")

            # Initial setup: Get all SMS and publish only unread ones
            last_sms_count = 0
            first_run = True

            while self.connected and not self.disconnecting:
                from support import retrieveAllSms, deleteSms

                # Check for new SMS with connectivity tracking (this will handle errors and update status)
                try:
                    all_sms = self.track_gammu_operation("retrieveAllSms", retrieveAllSms, gammu_machine)
                    current_count = len(all_sms)
                    logger.info(f"✅ SMS monitoring cycle OK: {current_count} messages on SIM")
                except Exception as e:
                    # track_gammu_operation already recorded the failure and published status
                    logger.warning(f"❌ SMS monitoring cycle failed (modem offline): {e}")

                    # After 2 consecutive failures, attempt soft reset to recover connection
                    # Then retry every 5 failures (5, 10, 15, 20...)
                    failures = self.device_tracker.consecutive_failures
                    if failures == 2 or (failures > 2 and failures % 5 == 0):
                        logger.warning(f"🔄 Attempting modem soft reset after {failures} failures...")
                        try:
                            # Soft reset: AT+CFUN=1,1 (restart modem software, keep SIM state)
                            self.track_gammu_operation("Reset", gammu_machine.Reset, False)
                            logger.info("✅ Modem soft reset completed, waiting 5s for recovery...")
                            time.sleep(5)
                        except Exception as reset_err:
                            logger.error(f"❌ Modem soft reset failed: {reset_err}")

                    time.sleep(check_interval)
                    continue

                try:
                    if first_run:
                        # On first run, publish only unread SMS and process delivery reports
                        logger.info(f"📱 Initial SMS check: {current_count} total SMS on SIM")
                        unread_count = 0
                        delivery_reports_processed = 0
                        deleted_count = 0
                        
                        for i, sms in enumerate(all_sms):
                            # Check if this is a delivery report (process even if read)
                            if self.config.get('sms_delivery_reports', False):
                                sms_type = sms.get('Type', '')
                                if sms_type == 'Status_Report':
                                    message_ref = sms.get('MessageReference', None)
                                    status = sms.get('DeliveryStatus', 'unknown')
                                    
                                    if message_ref:
                                        delivery_info = self.delivery_tracker.update_delivery_status(
                                            message_ref, status
                                        )
                                        if delivery_info:
                                            self.publish_delivery_report(message_ref, status, delivery_info)
                                            delivery_reports_processed += 1
                                    
                                    # Auto-delete delivery report
                                    try:
                                        self.track_gammu_operation("deleteSms", deleteSms, gammu_machine, all_sms[i])
                                        logger.debug(f"🗑️ Auto-deleted delivery report (ref={message_ref})")
                                        deleted_count += 1
                                    except Exception as e:
                                        logger.error(f"Error deleting delivery report: {e}")
                                    continue  # Skip publishing as regular SMS
                            
                            # Publish unread regular SMS
                            if sms.get('State') == 'UnRead':
                                sms_copy = sms.copy()
                                sms_copy.pop("Locations", None)
                                self.publish_sms_received(sms_copy)
                                unread_count += 1

                        if unread_count > 0:
                            logger.info(f"📱 Published {unread_count} unread SMS messages")
                        if delivery_reports_processed > 0:
                            logger.info(f"📬 Processed {delivery_reports_processed} delivery reports")
                        if deleted_count > 0:
                            logger.info(f"🗑️ Auto-deleted {deleted_count} delivery report(s)")
                        if unread_count == 0 and delivery_reports_processed == 0:
                            logger.info(f"📱 No unread messages or delivery reports")

                        # If we deleted any delivery reports, update SMS capacity
                        if deleted_count > 0:
                            try:
                                capacity = self.track_gammu_operation("GetSMSStatus", gammu_machine.GetSMSStatus)
                                self.publish_sms_capacity(capacity)
                                # Update count to reflect deleted delivery reports
                                current_count = capacity.get('SIMUsed', 0) + capacity.get('PhoneUsed', 0)
                                logger.info(f"📊 After deleting delivery reports: {current_count} SMS remaining on SIM")
                            except Exception as e:
                                logger.warning(f"Could not update SMS capacity after deleting delivery reports: {e}")

                        last_sms_count = current_count
                        first_run = False
                    elif current_count > last_sms_count:
                        # On subsequent runs, publish all new SMS
                        logger.info(f"📱 Detected {current_count - last_sms_count} new SMS messages")

                        deleted_count = 0
                        auto_delete = self.config.get('auto_delete_read_sms', False)

                        # Process new SMS (from the end, newest first)
                        for i in range(last_sms_count, current_count):
                            if i < len(all_sms):
                                sms = all_sms[i].copy()
                                sms.pop("Locations", None)

                                # Check if this is a delivery report
                                if self.config.get('sms_delivery_reports', False):
                                    sms_type = sms.get('Type', '')
                                    if sms_type == 'Status_Report':
                                        # This is a delivery report
                                        message_ref = sms.get('MessageReference', None)
                                        status = sms.get('DeliveryStatus', 'unknown')
                                        
                                        if message_ref:
                                            # Update delivery tracking
                                            delivery_info = self.delivery_tracker.update_delivery_status(
                                                message_ref, status
                                            )
                                            
                                            if delivery_info:
                                                # Publish delivery report
                                                self.publish_delivery_report(message_ref, status, delivery_info)
                                                logger.info(f"📬 Processed delivery report: ref={message_ref}, status={status}")
                                        
                                        # Don't publish delivery reports as regular SMS
                                        # Auto-delete delivery report
                                        try:
                                            self.track_gammu_operation("deleteSms", deleteSms, gammu_machine, all_sms[i])
                                            logger.debug(f"🗑️ Auto-deleted delivery report (ref={message_ref})")
                                            deleted_count += 1
                                        except Exception as e:
                                            logger.error(f"Error deleting delivery report: {e}")
                                        continue  # Skip regular SMS processing

                                # Publish regular SMS to MQTT
                                self.publish_sms_received(sms)

                                # Auto-delete if enabled and SMS is read
                                if auto_delete and sms.get('State') in ['Read', 'UnRead']:
                                    try:
                                        self.track_gammu_operation("deleteSms", deleteSms, gammu_machine, all_sms[i])
                                        logger.info(f"🗑️ Auto-deleted SMS from {sms.get('Number', 'Unknown')}")
                                        deleted_count += 1
                                    except Exception as e:
                                        logger.error(f"Error auto-deleting SMS: {e}")

                        # If we deleted any SMS (delivery reports or auto-delete), update capacity and get new count
                        if deleted_count > 0:
                            try:
                                capacity = self.track_gammu_operation("GetSMSStatus", gammu_machine.GetSMSStatus)
                                self.publish_sms_capacity(capacity)
                                # Update count to reflect deleted SMS
                                current_count = capacity.get('SIMUsed', 0) + capacity.get('PhoneUsed', 0)
                                logger.info(f"📊 After deleting {deleted_count} SMS: {current_count} remaining on SIM")
                            except Exception as e:
                                logger.warning(f"Could not update SMS capacity after deletion: {e}")

                    last_sms_count = current_count

                except Exception as e:
                    # Non-gammu errors (like MQTT publishing errors)
                    logger.error(f"Error processing SMS data: {e}")

                time.sleep(check_interval)
        
        # Only start if both MQTT and SMS monitoring are enabled  
        if (self.config.get('mqtt_enabled', False) and 
            self.config.get('sms_monitoring_enabled', True)):
            thread = threading.Thread(target=_sms_monitor_loop, daemon=True)
            thread.start()
    
    def publish_status_periodic(self, gammu_machine, interval=60):
        """Publish status data periodically in background thread"""
        if not self.connected:
            return
            
        def _publish_loop():
            while self.connected and not self.disconnecting:
                # Publish signal strength with connectivity tracking
                try:
                    signal = self.track_gammu_operation("GetSignalQuality", gammu_machine.GetSignalQuality)
                    # Filter out invalid BER value (-1 means not available)
                    if signal.get("BitErrorRate") == -1:
                        signal["BitErrorRate"] = None
                    self.publish_signal_strength(signal)
                except Exception as e:
                    # track_gammu_operation already recorded the failure
                    pass  # Warning already logged by track_gammu_operation

                # Publish network info with connectivity tracking
                try:
                    from gammu import GSMNetworks
                    network = self.track_gammu_operation("GetNetworkInfo", gammu_machine.GetNetworkInfo)
                    network_code = network.get("NetworkCode", "")
                    network_name = network.get("NetworkName")
                    
                    # Try multiple lookup methods if name is empty (Gammu bug: https://github.com/gammu/python-gammu/issues/31)
                    if not network_name and network_code:
                        # First try our comprehensive database
                        network_name = get_network_name(network_code)
                        # Fallback to Gammu's database
                        if not network_name:
                            network_name = GSMNetworks.get(network_code, 'Unknown')
                    
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
                    
                    self.publish_network_info(network)
                except Exception as e:
                    # track_gammu_operation already recorded the failure
                    pass  # Warning already logged by track_gammu_operation

                time.sleep(interval)
        
        if self.config.get('mqtt_enabled', False):
            thread = threading.Thread(target=_publish_loop, daemon=True)
            thread.start()
            logger.info(f"Started MQTT periodic publishing (interval: {interval}s)")
    
    def disconnect(self):
        """Disconnect from MQTT broker - thread-safe with duplicate call prevention"""
        if self.disconnecting:
            logger.debug("Disconnect already in progress, skipping")
            return

        self.disconnecting = True

        if self.client and self.connected:
            # Publish offline availability - makes ALL entities unavailable in HA
            try:
                self.client.publish(self.availability_topic, "offline", qos=1, retain=True)
                logger.info("📡 Published availability: offline (all entities now unavailable)")
                time.sleep(0.5)  # Give time for message to be sent
            except Exception as e:
                logger.warning(f"Could not publish offline availability: {e}")

            try:
                self.client.loop_stop()
                self.client.disconnect()
                self.connected = False
                logger.info("✅ Disconnected from MQTT broker successfully")
            except Exception as e:
                logger.error(f"Error during MQTT disconnect: {e}")
        else:
            logger.debug("MQTT client not connected, nothing to disconnect")