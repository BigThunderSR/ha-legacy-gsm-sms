#!/usr/bin/env python3
"""Standalone GSM SMS service for Home Assistant addon."""

import json
import logging
import os
import sys
import time
from datetime import datetime

import gammu
import requests

# Configure logging
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

log_level_str = os.environ.get("LOG_LEVEL", "info").lower()
log_level = LOG_LEVELS.get(log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

_LOGGER = logging.getLogger("gsm_sms_service")


class GSMSMSService:
    """Service to handle SMS via GSM modem."""

    def __init__(self):
        """Initialize the service."""
        # Get configuration from environment
        self.device = os.environ.get("DEVICE", "/dev/ttyUSB0")
        self.baud_speed = os.environ.get("BAUD_SPEED", "0")
        self.scan_interval = int(os.environ.get("SCAN_INTERVAL", "30"))
        
        # Home Assistant API
        self.ha_url = os.environ.get("SUPERVISOR_API", "http://supervisor/core")
        self.ha_token = os.environ.get("SUPERVISOR_TOKEN", "")
        self.headers = {
            "Authorization": f"Bearer {self.ha_token}",
            "Content-Type": "application/json",
        }
        
        # State
        self.sm = None
        self.connected = False
        self.signal_strength = None
        self.network_name = None
        self.device_manufacturer = None
        self.device_model = None
        
        _LOGGER.info(f"Initialized with device: {self.device}, baud: {self.baud_speed}")

    def connect(self):
        """Connect to the GSM modem."""
        try:
            # First, try to open the device file directly to test permissions
            _LOGGER.info(f"Testing direct access to {self.device}...")
            try:
                with open(self.device, 'rb') as f:
                    _LOGGER.info(f"Successfully opened device file for reading")
                with open(self.device, 'wb') as f:
                    _LOGGER.info(f"Successfully opened device file for writing")
            except Exception as e:
                _LOGGER.error(f"Cannot access device file directly: {e}")
                _LOGGER.error(f"This indicates a permissions/security issue at the container level")
                raise
            
            self.sm = gammu.StateMachine()
            
            # Configure connection
            connection_mode = "at"
            if self.baud_speed != "0":
                connection_mode += self.baud_speed
            
            config = {
                "Device": self.device,
                "Connection": connection_mode,
            }
            
            _LOGGER.info(f"Connecting to modem with config: {config}")
            self.sm.SetConfig(0, config)
            self.sm.Init()
            
            # Get device info
            try:
                self.device_manufacturer = self.sm.GetManufacturer()
                self.device_model = self.sm.GetModel()[0]
                _LOGGER.info(f"Connected to {self.device_manufacturer} {self.device_model}")
            except Exception as e:
                _LOGGER.warning(f"Could not get device info: {e}")
            
            self.connected = True
            return True
            
        except Exception as e:
            _LOGGER.error(f"Failed to connect to modem: {e}")
            self.connected = False
            return False

    def update_signal_strength(self):
        """Update signal strength."""
        if not self.connected or not self.sm:
            return
        
        try:
            signal = self.sm.GetSignalQuality()
            self.signal_strength = signal.get("SignalPercent", -1)
            _LOGGER.debug(f"Signal strength: {self.signal_strength}%")
        except Exception as e:
            _LOGGER.error(f"Error getting signal strength: {e}")
            self.signal_strength = -1

    def update_network_info(self):
        """Update network information."""
        if not self.connected or not self.sm:
            return
        
        try:
            network = self.sm.GetNetworkInfo()
            self.network_name = network.get("NetworkName", "Unknown")
            _LOGGER.debug(f"Network: {self.network_name}")
        except Exception as e:
            _LOGGER.error(f"Error getting network info: {e}")
            self.network_name = "Unknown"

    def check_messages(self):
        """Check for new SMS messages."""
        if not self.connected or not self.sm:
            return
        
        try:
            # Get SMS status
            status = self.sm.GetSMSStatus()
            total_messages = status.get("SIMUsed", 0) + status.get("PhoneUsed", 0)
            
            if total_messages == 0:
                _LOGGER.debug("No messages to read")
                return
            
            _LOGGER.info(f"Found {total_messages} messages to read")
            
            # Read all messages
            messages = []
            sms = None
            start = True
            
            while True:
                try:
                    if start:
                        sms = self.sm.GetNextSMS(Folder=0, Start=True)
                        start = False
                    else:
                        if sms is None:
                            break
                        sms = self.sm.GetNextSMS(Folder=0, Location=sms[0]["Location"])
                    
                    messages.append(sms)
                    
                    # Delete the message
                    try:
                        self.sm.DeleteSMS(Folder=0, Location=sms[0]["Location"])
                    except Exception as e:
                        _LOGGER.warning(f"Could not delete message: {e}")
                        
                except gammu.ERR_EMPTY:
                    break
                except Exception as e:
                    _LOGGER.error(f"Error reading messages: {e}")
                    break
            
            # Process messages
            for msg_parts in messages:
                try:
                    # Link multipart messages
                    linked = gammu.LinkSMS([msg_parts])
                    
                    for msg in linked:
                        decoded = gammu.DecodeSMS(msg)
                        sms_info = msg[0]
                        
                        # Extract text
                        if decoded is None:
                            text = sms_info.get("Text", "")
                        else:
                            text = "".join(
                                entry.get("Buffer", "")
                                for entry in decoded.get("Entries", [])
                                if entry.get("Buffer")
                            )
                        
                        # Fire event to Home Assistant
                        event_data = {
                            "phone": sms_info.get("Number", "Unknown"),
                            "date": str(sms_info.get("DateTime", datetime.now())),
                            "text": text,
                        }
                        
                        _LOGGER.info(f"Received SMS from {event_data['phone']}: {event_data['text']}")
                        self.fire_event("legacy_gsm_sms.incoming_sms", event_data)
                        
                except Exception as e:
                    _LOGGER.error(f"Error processing message: {e}")
                    
        except Exception as e:
            _LOGGER.error(f"Error checking messages: {e}")

    def fire_event(self, event_type, event_data):
        """Fire an event to Home Assistant."""
        try:
            url = f"{self.ha_url}/api/events/{event_type}"
            response = requests.post(url, headers=self.headers, json=event_data, timeout=10)
            
            if response.status_code == 200:
                _LOGGER.debug(f"Event fired successfully: {event_type}")
            else:
                _LOGGER.error(f"Failed to fire event: {response.status_code} - {response.text}")
                
        except Exception as e:
            _LOGGER.error(f"Error firing event: {e}")

    def update_sensors(self):
        """Update sensor states in Home Assistant."""
        if not self.connected:
            return
        
        sensors = {
            "sensor.gsm_signal_strength": {
                "state": self.signal_strength if self.signal_strength is not None else "unknown",
                "attributes": {
                    "unit_of_measurement": "%",
                    "device_class": "signal_strength",
                    "friendly_name": "GSM Signal Strength",
                }
            },
            "sensor.gsm_network": {
                "state": self.network_name if self.network_name else "unknown",
                "attributes": {
                    "friendly_name": "GSM Network",
                }
            },
        }
        
        for entity_id, data in sensors.items():
            try:
                url = f"{self.ha_url}/api/states/{entity_id}"
                payload = {
                    "state": data["state"],
                    "attributes": data["attributes"],
                }
                response = requests.post(url, headers=self.headers, json=payload, timeout=10)
                
                if response.status_code in [200, 201]:
                    _LOGGER.debug(f"Updated {entity_id}")
                else:
                    _LOGGER.warning(f"Failed to update {entity_id}: {response.status_code}")
                    
            except Exception as e:
                _LOGGER.error(f"Error updating sensor {entity_id}: {e}")

    def run(self):
        """Run the main service loop."""
        _LOGGER.info("GSM SMS Service starting...")
        
        # Try to connect
        retry_count = 0
        max_retries = 5
        
        while retry_count < max_retries and not self.connected:
            if self.connect():
                break
            
            retry_count += 1
            _LOGGER.warning(f"Connection attempt {retry_count}/{max_retries} failed, retrying in 10 seconds...")
            time.sleep(10)
        
        if not self.connected:
            _LOGGER.error("Failed to connect to modem after all retries. Exiting.")
            sys.exit(1)
        
        _LOGGER.info("GSM SMS Service running!")
        
        # Main loop
        while True:
            try:
                # Update modem info
                self.update_signal_strength()
                self.update_network_info()
                
                # Check for messages
                self.check_messages()
                
                # Update Home Assistant sensors
                self.update_sensors()
                
                # Wait for next scan
                time.sleep(self.scan_interval)
                
            except KeyboardInterrupt:
                _LOGGER.info("Shutting down...")
                break
            except Exception as e:
                _LOGGER.error(f"Error in main loop: {e}")
                time.sleep(10)


if __name__ == "__main__":
    service = GSMSMSService()
    service.run()
