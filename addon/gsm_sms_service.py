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

# Set up logging
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
        self.ha_url = os.environ.get("SUPERVISOR_API") or "http://supervisor/core"
        self.ha_token = os.environ.get("SUPERVISOR_TOKEN", "")
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
                gammu_config["Baudrate"] = self.baud_speed
            
            # Initialize Gammu state machine
            self.sm = gammu.StateMachine()
            self.sm.SetConfig(0, gammu_config)
            self.sm.Init()
            
            _LOGGER.info("Modem initialized successfully")
            self.connected = True
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
            data = {
                "state": state,
                "attributes": {}
            }
            
            if unit:
                data["attributes"]["unit_of_measurement"] = unit
                
            url = f"{self.ha_url}/api/states/{entity_id}"
            response = requests.post(url, headers=self.headers, json=data)
            
            if response.status_code not in (200, 201):
                _LOGGER.error("Failed to update sensor %s: %s", entity_id, response.text)
        except Exception as ex:
            _LOGGER.error("Error updating sensor: %s", str(ex))

    def _fire_ha_event(self, event_type, event_data):
        """Fire an event in Home Assistant."""
        try:
            url = f"{self.ha_url}/api/events/{event_type}"
            response = requests.post(url, headers=self.headers, json=event_data)
            
            if response.status_code != 200:
                _LOGGER.error("Failed to fire event %s: %s", event_type, response.text)
        except Exception as ex:
            _LOGGER.error("Error firing event: %s", str(ex))
            
    def register_service(self):
        """Register the notify service in Home Assistant."""
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
            
            url = f"{self.ha_url}/api/services/notify/{self.service_name}"
            response = requests.post(url, headers=self.headers, json=service_data)
            
            if response.status_code not in (200, 201):
                _LOGGER.error("Failed to register notify service: %s", response.text)
            else:
                _LOGGER.info("Notify service registered successfully")
        except Exception as ex:
            _LOGGER.error("Error registering service: %s", str(ex))

    def listen_for_service_calls(self):
        """Start a thread to listen for service calls."""
        import threading
        import time
        import json

        def listener():
            _LOGGER.info(f"Starting service call listener for notify.{self.service_name}")
            
            # Define the endpoint to poll for service calls
            url = f"{self.ha_url}/api/services/notify/{self.service_name}/history"
            
            last_check_time = datetime.now().isoformat()
            
            while True:
                try:
                    # Poll for new service calls
                    response = requests.get(
                        url, 
                        headers=self.headers,
                        params={"since": last_check_time}
                    )
                    
                    if response.status_code == 200:
                        service_calls = response.json()
                        for call in service_calls:
                            try:
                                # Process the service call
                                _LOGGER.info(f"Received service call: {call}")
                                
                                data = call.get("data", {})
                                message = data.get("message", "")
                                targets = data.get("target", [])
                                
                                if isinstance(targets, str):
                                    targets = [targets]
                                
                                # Send SMS to each target
                                for target in targets:
                                    self.send_sms(target, message)
                                    
                            except Exception as ex:
                                _LOGGER.error(f"Error processing service call: {ex}")
                        
                        last_check_time = datetime.now().isoformat()
                except Exception as ex:
                    _LOGGER.error(f"Error polling for service calls: {ex}")
                
                # Sleep for a short period before polling again
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


if __name__ == "__main__":
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            # Load configuration
            try:
                with open('/data/gsm_sms/config.json', 'r') as f:
                    config = json.load(f)
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
