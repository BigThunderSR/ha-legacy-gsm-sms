#!/usr/bin/env python3
"""Standalone GSM SMS service for Home Assistant addon."""

import json
import logging
import os
import sys
import time
from datetime import datetime
import requests
import gammu

# Default to INFO level until we load the config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# For s6-overlay compatibility
os.environ['PYTHONUNBUFFERED'] = '1'

_LOGGER = logging.getLogger("gsm_sms_service")

# Function to set log level from string
def set_log_level(level_str):
    """Set the log level based on a string value from config."""
    log_levels = {
        "trace": logging.DEBUG,  # Treat trace as debug for Python
        "debug": logging.DEBUG,
        "info": logging.INFO, 
        "notice": logging.INFO,  # Treat notice as info for Python
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "fatal": logging.CRITICAL
    }
    
    # Default to INFO if the level is not recognized
    level = log_levels.get(level_str.lower(), logging.INFO)
    _LOGGER.setLevel(level)
    
    # Also set the root logger
    logging.getLogger().setLevel(level)
    
    # Log the change
    _LOGGER.info(f"Log level set to: {level_str} ({logging.getLevelName(level)})")
    
    # Special case for debug level - print extra information
    if level == logging.DEBUG:
        _LOGGER.debug("====== GSM SMS Service Debug Information ======")
        _LOGGER.debug(f"Python version: {sys.version}")
        _LOGGER.debug(f"Current working directory: {os.getcwd()}")
        _LOGGER.debug(f"Current user: {os.getuid()}")
        _LOGGER.debug(f"Environment variables: {os.environ}")
        _LOGGER.debug("=============================================")

# Print startup diagnostic information
_LOGGER.debug("====== GSM SMS Service Debug Information ======")
_LOGGER.debug(f"Python version: {sys.version}")
_LOGGER.debug(f"Current working directory: {os.getcwd()}")
_LOGGER.debug(f"Current user: {os.getuid()}")
_LOGGER.debug(f"Environment variables: {os.environ}")
_LOGGER.debug("============================================")

class GSMSMSService:
    """Service to handle SMS via GSM modem."""

    def __init__(self, config):
        """Initialize the service."""
        self.device = config.get("device", "/dev/ttyUSB0")
        self.baud_speed = config.get("baud_speed", "0")
        self.unicode = config.get("unicode", False)
        self.scan_interval = config.get("scan_interval", 30)
        self.service_name = config.get("service_name", "legacy_gsm_sms")
        self.sm = None
        
        # Device information - will be populated when modem connects
        self.device_manufacturer = None
        self.device_model = None
        self.device_imei = None
        
        # Get Home Assistant connection details from environment
        self.ha_url = os.environ.get("SUPERVISOR_API") or "http://supervisor/core"
        self.ha_token = os.environ.get("SUPERVISOR_TOKEN", "")
        
        # Log connection details (redact token for security)
        _LOGGER.info(f"Home Assistant URL: {self.ha_url}")
        _LOGGER.debug(f"Home Assistant token available: {bool(self.ha_token)}")
        
        self.headers = {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json",
        }
        self.signal_strength = None
        self.network_name = None
        self.connected = False
        self.last_read_time = datetime.now()

    def setup_modem(self):
        """Set up the GSM modem."""
        _LOGGER.info("Setting up GSM modem: %s", self.device)
        
        try:
            # Wait for the device to be available
            if not os.path.exists(self.device):
                _LOGGER.warning("Device %s does not exist, checking available devices", self.device)
                
                # List available devices
                tty_devices = [d for d in os.listdir("/dev") if d.startswith("tty")]
                _LOGGER.info("Available tty devices: %s", ", ".join(tty_devices))
                
                # Wait and retry
                _LOGGER.info("Waiting for device to become available...")
                return False
            
            # Gammu configuration
            gammu_config = {
                "Device": self.device,
                "Connection": "at",
            }
            
            if self.baud_speed != "0":
                gammu_config["Speed"] = self.baud_speed
                # Note: Do not use "Baudrate" as it's not recognized by Gammu
            
            # Initialize Gammu state machine
            self.sm = gammu.StateMachine()
            self.sm.SetConfig(0, gammu_config)
            self.sm.Init()
            
            _LOGGER.info("Modem initialized successfully")
            self.connected = True
            
            # Get device information from the modem
            self.get_device_info()
            
            return True
        except gammu.ERR_DEVICENOTEXIST:
            _LOGGER.error("Device %s does not exist", self.device)
            self.connected = False
            return False
        except gammu.GSMError as e:
            _LOGGER.error("Failed to initialize modem: %s", str(e))
            self.connected = False
            return False
        except Exception as e:
            _LOGGER.error("Unexpected error initializing modem: %s", str(e))
            self.connected = False
            return False

    def update_signal_info(self):
        """Update signal strength and network information."""
        try:
            if not self.sm or not self.connected:
                return
                
            signal_quality = self.sm.GetSignalQuality()
            self.signal_strength = signal_quality["SignalPercent"]
            
            net_info = self.sm.GetNetworkInfo()
            self.network_name = net_info.get("NetworkName", "Unknown")
            
            _LOGGER.debug(
                "Signal: %s%%, Network: %s",
                self.signal_strength,
                self.network_name
            )
            
            # Update the Home Assistant sensor states
            self._update_ha_sensor(f"sensor.{self.service_name}_signal_strength", self.signal_strength, "%")
            self._update_ha_sensor(f"sensor.{self.service_name}_network_name", self.network_name)
            
            # Add a last_update sensor to track when data was last refreshed
            self._update_ha_sensor(f"sensor.{self.service_name}_last_update", datetime.now().isoformat())
        except gammu.GSMError as ex:
            _LOGGER.error("Failed to update signal info: %s", str(ex))
            self.connected = False

    def check_for_new_sms(self):
        """Check for new SMS messages."""
        try:
            if not self.sm or not self.connected:
                return
                
            # Get status of messages in all folders
            status = self.sm.GetSMSStatus()
            remain = status["SIMUsed"] + status["PhoneUsed"] + status["TemplatesUsed"]
            
            _LOGGER.debug("Messages in phone: %s", remain)
            
            if remain > 0:
                # Get all sms
                sms = []
                entry = None
                
                # Get first message
                try:
                    entry = self.sm.GetNextSMS(Start=True, Folder=0)
                    if entry:
                        sms.append(entry)
                        
                    # Get remaining messages
                    while entry and len(entry) > 0:
                        last_location = entry[0].get("Location", 0)
                        entry = self.sm.GetNextSMS(Location=last_location, Folder=0)
                        if entry:
                            sms.append(entry)
                        
                except gammu.ERR_EMPTY:
                    # This is expected, means we've read all messages
                    pass
                
                # Process the messages
                for message in sms:
                    self._process_sms_message(message)
                
        except gammu.GSMError as ex:
            _LOGGER.error("Failed to check for new SMS: %s", str(ex))
            self.connected = False

    def _process_sms_message(self, message):
        """Process received SMS message."""
        if not self.sm or not self.connected:
            _LOGGER.warning("Cannot process SMS: modem not connected")
            return
            
        for single in message:
            # Only process unread messages
            if single["State"] == "UnRead":
                try:
                    # Mark message as read
                    self.sm.DeleteSMS(0, single["Location"])
                except gammu.GSMError as ex:
                    _LOGGER.error("Failed to mark SMS as read: %s", str(ex))
                except Exception as ex:
                    _LOGGER.error("Unexpected error marking SMS as read: %s", str(ex))
                
                try:
                    decoded_message = {
                        "phone": single["Number"],
                        "date": single["DateTime"].strftime("%Y-%m-%d %H:%M:%S"),
                        "text": single["Text"],
                    }
                    
                    _LOGGER.info(
                        "Received SMS from %s: %s",
                        decoded_message["phone"],
                        decoded_message["text"]
                    )
                    
                    # Fire event in Home Assistant
                    self._fire_ha_event(f"{self.service_name}.incoming_sms", decoded_message)
                except Exception as ex:
                    _LOGGER.error("Error processing SMS content: %s", str(ex))

    def send_sms(self, to, message):
        """Send SMS message."""
        if not self.sm or not self.connected:
            _LOGGER.error("Cannot send SMS: Modem not connected")
            return False
            
        try:
            # Prepare message data
            sms_info = {
                "Class": -1,
                "Unicode": self.unicode,
                "Entries": [
                    {
                        "ID": "ConcatenatedTextLong",
                        "Buffer": message,
                    }
                ],
            }
            
            # Encode message
            encoded_sms = gammu.EncodeSMS(sms_info)
            
            # Send the message parts
            for sms in encoded_sms:
                sms["SMSC"] = {"Location": 1}
                sms["Number"] = to
                self.sm.SendSMS(sms)
            
            _LOGGER.info("SMS sent to %s", to)
            return True
        except gammu.GSMError as ex:
            _LOGGER.error("Failed to send SMS: %s", str(ex))
            return False

    def _update_ha_sensor(self, entity_id, state, unit=None):
        """Update a sensor state in Home Assistant."""
        try:
            # Extract the sensor name from entity_id (removing the sensor. prefix)
            sensor_name = entity_id.replace('sensor.', '')
            
            # Create a unique_id based on the entity_id but without the domain prefix
            unique_id = f"gsm_sms_{sensor_name}"
            
            # Prepare attributes and metadata based on sensor type
            attributes = {
                "friendly_name": sensor_name.replace('_', ' ').title(),
            }
            
            # Set specific metadata based on sensor type
            if "signal_strength" in entity_id:
                attributes["device_class"] = "signal_strength"
                attributes["state_class"] = "measurement"
                attributes["icon"] = "mdi:signal"
            elif "network_name" in entity_id:
                attributes["icon"] = "mdi:network"
            elif "manufacturer" in entity_id:
                attributes["icon"] = "mdi:factory"
            elif "model" in entity_id:
                attributes["icon"] = "mdi:cellphone"
            elif "last_update" in entity_id:
                attributes["device_class"] = "timestamp"
                attributes["icon"] = "mdi:clock-outline"
            
            data = {
                "state": state,
                "attributes": attributes
            }
            
            # Add unique_id to make the entity persistent
            data["unique_id"] = unique_id
            
            # Add device info to group all entities under one device in the UI
            device_info = {
                "identifiers": [f"gsm_sms_{self.service_name}"],
                "name": f"GSM SMS {self.service_name}",
                "sw_version": "0.0.1g"  # Match the addon version
            }
            
            # Use real device info if available
            if self.device_manufacturer:
                device_info["manufacturer"] = self.device_manufacturer
            else:
                device_info["manufacturer"] = "Home Assistant Add-on"
                
            if self.device_model:
                device_info["model"] = self.device_model
            else:
                device_info["model"] = "GSM Modem"
                
            if self.device_imei:
                # Add IMEI as a secondary identifier
                device_info["identifiers"].append(f"imei_{self.device_imei}")
                
            data["device"] = device_info
            
            if unit:
                data["attributes"]["unit_of_measurement"] = unit
                
            # Skip if no token
            if not self.ha_token:
                _LOGGER.debug(f"No Home Assistant token, skipping sensor update for {entity_id}")
                return
                
            url = f"{self.ha_url}/api/states/{entity_id}"
            try:
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
                
                if response.status_code not in (200, 201):
                    _LOGGER.error(f"Failed to update sensor {entity_id}: HTTP {response.status_code} - {response.text}")
                else:
                    _LOGGER.debug(f"Successfully updated sensor {entity_id}")
            except requests.exceptions.RequestException as e:
                _LOGGER.error(f"Error connecting to Home Assistant: {str(e)}")
        except Exception as ex:
            _LOGGER.error("Error updating sensor: %s", str(ex))

    def _fire_ha_event(self, event_type, event_data):
        """Fire an event in Home Assistant."""
        try:
            # Skip if no token
            if not self.ha_token:
                _LOGGER.debug(f"No Home Assistant token, skipping event {event_type}")
                return
                
            url = f"{self.ha_url}/api/events/{event_type}"
            
            try:
                response = requests.post(url, headers=self.headers, json=event_data, timeout=10)
                
                if response.status_code != 200:
                    _LOGGER.error(f"Failed to fire event {event_type}: HTTP {response.status_code} - {response.text}")
                else:
                    _LOGGER.debug(f"Successfully fired event {event_type}")
            except requests.exceptions.RequestException as e:
                _LOGGER.error(f"Error connecting to Home Assistant: {str(e)}")
        except Exception as ex:
            _LOGGER.error("Error firing event: %s", str(ex))
            
    def register_service(self):
        """Register the notify service in Home Assistant."""
        
        # Skip registration if token is empty
        if not self.ha_token:
            _LOGGER.warning("No Home Assistant token provided, skipping service registration")
            return
            
        try:
            # Create a service for sending SMS
            service_data = {
                "domain": "notify",
                "service": self.service_name,
                "service_data": {
                    "message": "{{ message }}",
                    "target": "{{ target }}"
                },
                "target": {
                    "entity_id": f"notify.{self.service_name}"
                }
            }
            
            _LOGGER.info(f"Registering notify service with Home Assistant at {self.ha_url}")
            
            url = f"{self.ha_url}/api/services/notify/{self.service_name}"
            
            try:
                response = requests.post(url, headers=self.headers, json=service_data, timeout=10)
                
                if response.status_code not in (200, 201):
                    _LOGGER.error(f"Failed to register notify service: HTTP {response.status_code} - {response.text}")
                else:
                    _LOGGER.info("Successfully registered notify service")
            except requests.exceptions.RequestException as e:
                _LOGGER.error(f"Error connecting to Home Assistant: {str(e)}")
                return
                _LOGGER.info("Notify service registered successfully")
        except Exception as ex:
            _LOGGER.error("Error registering service: %s", str(ex))

    def listen_for_service_calls(self):
        """Start a thread to listen for service calls."""
        import threading
        import time
        import json
        
        # Don't start listener if no HA token
        if not self.ha_token:
            _LOGGER.warning("No Home Assistant token, service call listener not started")
            return

        def listener():
            """Monitor for SMS requests through files."""
            _LOGGER.info(f"Starting service call listener for notify.{self.service_name}")
            
            # Instead of polling Home Assistant API, we'll use a file-based approach
            # This avoids issues with non-existent API endpoints like /core/api/services/notify/{service_name}/history
            sms_dir = "/data/gsm_sms/pending"
            os.makedirs(sms_dir, exist_ok=True)
            
            _LOGGER.info(f"Monitoring directory for SMS requests: {sms_dir}")
            
            while True:
                try:
                    # Look for pending SMS files
                    sms_files = [f for f in os.listdir(sms_dir) if f.endswith('.sms')]
                    
                    for sms_file in sms_files:
                        file_path = os.path.join(sms_dir, sms_file)
                        _LOGGER.debug(f"Found SMS request file: {sms_file}")
                        
                        try:
                            # Read the SMS data from file
                            with open(file_path, 'r') as f:
                                sms_data = json.load(f)
                            
                            # Process the SMS data
                            message = sms_data.get("message", "")
                            targets = sms_data.get("target", [])
                            
                            if not message:
                                _LOGGER.warning(f"Empty message in SMS request file: {sms_file}")
                            
                            if not targets:
                                _LOGGER.warning(f"No targets in SMS request file: {sms_file}")
                            
                            if isinstance(targets, str):
                                targets = [targets]
                            
                            # Send SMS to each target
                            for target in targets:
                                _LOGGER.info(f"Sending SMS to {target}: {message}")
                                self.send_sms(target, message)
                            
                            # Delete the file after processing
                            os.remove(file_path)
                            _LOGGER.debug(f"Processed and removed SMS file: {sms_file}")
                            
                        except Exception as ex:
                            _LOGGER.error(f"Error processing SMS file {sms_file}: {ex}")
                            # Move the file to an error directory
                            error_dir = os.path.join(sms_dir, "errors")
                            os.makedirs(error_dir, exist_ok=True)
                            try:
                                os.rename(file_path, os.path.join(error_dir, sms_file))
                            except:
                                # If moving fails, just try to delete it
                                try:
                                    os.remove(file_path)
                                except:
                                    pass
                
                except Exception as ex:
                    _LOGGER.error(f"Error in service call listener: {ex}")
                
                # Sleep for a short period before checking again
                time.sleep(5)
                
        # Start the listener thread
        thread = threading.Thread(target=listener)
        thread.daemon = True
        thread.start()
    
    def run(self):
        """Run the service."""
        _LOGGER.info("Starting GSM SMS Service")
        
        # Register the service with Home Assistant
        self.register_service()
        
        # Start service call listener
        self.listen_for_service_calls()
        
        last_signal_update = 0
        
        while True:
            # Try to setup/reconnect the modem if not connected
            if not self.connected:
                self.setup_modem()
                time.sleep(5)
                continue
                
            current_time = time.time()
            
            # Update signal info every minute
            if current_time - last_signal_update > 60:
                self.update_signal_info()
                last_signal_update = current_time
            
            # Check for new messages according to scan interval
            self.check_for_new_sms()
            
            # Sleep for the configured scan interval
            time.sleep(self.scan_interval)

    def get_device_info(self):
        """Get device information from the modem."""
        if not self.sm or not self.connected:
            return
            
        try:
            # Get device information
            self.device_manufacturer = self.sm.GetManufacturer()
            _LOGGER.debug(f"Manufacturer: {self.device_manufacturer}")
            
            self.device_model = self.sm.GetModel()[0]
            _LOGGER.debug(f"Model: {self.device_model}")
            
            self.device_imei = self.sm.GetIMEI()
            _LOGGER.debug(f"IMEI: {self.device_imei}")
            
            # Report device information to Home Assistant
            self._update_ha_sensor(f"sensor.{self.service_name}_manufacturer", self.device_manufacturer)
            self._update_ha_sensor(f"sensor.{self.service_name}_model", self.device_model)
            
        except Exception as e:
            _LOGGER.error(f"Error getting device information: {e}")

if __name__ == "__main__":
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            # Load configuration
            try:
                with open('/data/gsm_sms/config.json', 'r') as f:
                    config = json.load(f)
                
                # Set log level from configuration
                log_level = config.get("log_level", "info")
                set_log_level(log_level)
                
            except FileNotFoundError:
                _LOGGER.error("Config file not found. Waiting for 10 seconds...")
                time.sleep(10)
                retry_count += 1
                continue
            except json.JSONDecodeError:
                _LOGGER.error("Invalid JSON in config file. Waiting for 10 seconds...")
                time.sleep(10)
                retry_count += 1
                continue
                
            # Create and run service
            service = GSMSMSService(config)
            
            # Give Home Assistant time to start up if needed
            _LOGGER.info("Waiting for Home Assistant to be ready...")
            time.sleep(10)
            
            # Run the service
            _LOGGER.info("Starting GSM SMS service main loop...")
            service.run()
            break
            
        except Exception as e:
            _LOGGER.error("Service error: %s", str(e))
            _LOGGER.info("Retrying in 30 seconds... (Attempt %d of %d)", retry_count + 1, max_retries)
            time.sleep(30)
            retry_count += 1
    
    if retry_count >= max_retries:
        _LOGGER.error("Maximum retry attempts reached. Exiting...")
        sys.exit(1)
