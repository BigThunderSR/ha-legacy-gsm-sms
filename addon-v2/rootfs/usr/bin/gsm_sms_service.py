#!/usr/bin/env python3
"""GSM SMS service using pyserial for Home Assistant addon.

NOTE: SMS reading via AT+CMGL is currently disabled because it causes
modem hangs/crashes on certain hardware (SimTech modems). This is a known
issue. SMS reception will need to be implemented via unsolicited +CMTI
notifications in a future update. SMS sending functionality works fine.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from threading import Thread, Lock

import serial  # type: ignore[import-not-found]
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

# GSM 7-bit alphabet for SMS encoding/decoding
GSM7_ALPHABET = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ"
    " !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
    "¿abcdefghijklmnopqrstuvwxyzäöñüà"
)


class GSMModem:
    """Handle GSM modem communication via serial port."""
    
    def __init__(self, device, baudrate=115200):
        """Initialize modem connection."""
        self.device = device
        self.baudrate = baudrate
        self.serial = None
        self.opened = False
        self.read_thread = None
        self.response_lock = Lock()
        self.ok_received = False
        self.prompt_received = False
        self.response_lines = []
        self.sms_list = []
        self.last_sms_text = b''
        self.recording_sms = False
        
        _LOGGER.info(f"GSM Modem initialized for device: {device}")
    
    def open(self):
        """Open serial connection to modem."""
        try:
            _LOGGER.info(f"Opening device on {self.device}")
            self.serial = serial.Serial()
            self.serial.port = self.device
            self.serial.baudrate = self.baudrate
            self.serial.parity = serial.PARITY_NONE
            self.serial.bytesize = serial.EIGHTBITS
            self.serial.stopbits = serial.STOPBITS_ONE
            self.serial.xonxoff = False
            self.serial.rtscts = False
            self.serial.dsrdtr = False
            self.serial.timeout = 1
            
            self.serial.open()
            
            if self.serial.is_open:
                self.opened = True
                self.serial.flush()
                _LOGGER.info(f"Device opened successfully on {self.device}")
                
                # Start read thread
                self.read_thread = Thread(target=self._read_loop, daemon=True)
                self.read_thread.start()
                return True
            else:
                _LOGGER.error(f"Device failed to open: {self.device}")
                return False
                
        except Exception as e:
            _LOGGER.error(f"Exception opening device {self.device}: {e}")
            return False
    
    def close(self):
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            _LOGGER.info("Closing GSM device")
            self.serial.close()
            self.opened = False
    
    def _read_loop(self):
        """Background thread to read from serial port."""
        frame = b''
        
        while self.opened and self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting >= 1:
                    data = self.serial.read(1)
                    frame += data
                    
                    # Check for prompt (> )
                    if b'> ' in frame:
                        self.ok_received = True
                        self.prompt_received = True
                        frame = b''
                    
                    # Check for line ending
                    elif b'\r\n' in frame:
                        line = frame.decode('ascii', errors='ignore').strip()
                        
                        if 'OK' in line:
                            self.ok_received = True
                            if self.recording_sms:
                                # Remove trailing CRLF from SMS text
                                if self.last_sms_text.endswith(b'\r\n\r\n'):
                                    self.last_sms_text = self.last_sms_text[:-4]
                                self.recording_sms = False
                        
                        elif '+CMGL:' in line:
                            # SMS list entry
                            parts = line.split(',')
                            if len(parts) >= 3:
                                msg_id = parts[0].split(':')[1].strip()
                                status = parts[1].strip().strip('"')
                                number = parts[2].strip().strip('"')
                                self.sms_list.append({
                                    'Id': msg_id,
                                    'Number': number,
                                    'Status': status
                                })
                        
                        elif '+CMGR:' in line:
                            # Start recording SMS text
                            self.recording_sms = True
                            self.last_sms_text = b''
                        
                        elif '+CME ERROR:' in line or 'ERROR' in line:
                            _LOGGER.debug(f"Modem error: {line}")
                            self.ok_received = True
                        
                        elif self.recording_sms:
                            # This is SMS text content
                            self.last_sms_text += frame
                        
                        frame = b''
                
                else:
                    time.sleep(0.001)
                    
            except Exception as e:
                _LOGGER.error(f"Error in read loop: {e}")
                time.sleep(0.1)
    
    def write_command(self, command, timeout=5):
        """Write AT command and wait for OK."""
        if not self.opened or not self.serial:
            return False
        
        self.ok_received = False
        cmd = command.encode('ascii') + b'\r'
        
        _LOGGER.debug(f"Sending: {command}")
        try:
            self.serial.write(cmd)
        except Exception as e:
            _LOGGER.error(f"Failed to write command: {e}")
            return False
        
        # Wait for OK response
        start = time.time()
        while not self.ok_received and (time.time() - start) < timeout:
            time.sleep(0.01)
        
        if not self.ok_received:
            _LOGGER.warning(f"Command timeout: {command}")
        
        return self.ok_received
    
    def write_data(self, data):
        """Write raw data to serial port."""
        if self.opened and self.serial:
            self.serial.write(data)
    
    def init_modem(self):
        """Initialize modem with AT commands."""
        _LOGGER.info("Initializing GSM modem...")
        
        # Basic commands only - don't configure SMS storage which might hang
        commands = [
            ("ATZ", "Reset modem", 3),
            ("ATE0", "Disable echo", 2),
            ("AT+CMGF=1", "Set SMS text mode", 2),
        ]
        
        for cmd, desc, timeout in commands:
            _LOGGER.debug(f"{desc}: {cmd}")
            if not self.write_command(cmd, timeout=timeout):
                _LOGGER.warning(f"Command may have failed: {cmd}")
            time.sleep(0.2)
        
        _LOGGER.info("Modem initialization complete")
    
    def get_signal_strength(self):
        """Get signal strength."""
        try:
            if self.write_command("AT+CSQ", timeout=2):
                return 99  # Unknown/not detectable
        except Exception as e:
            _LOGGER.debug(f"Error getting signal strength: {e}")
        return None
    
    def send_sms(self, number, message):
        """Send SMS message."""
        _LOGGER.info(f"Sending SMS to {number}")
        
        # Set up send command
        self.prompt_received = False
        if not self.write_command(f'AT+CMGS="{number}"'):
            _LOGGER.error("Failed to start SMS send")
            return False
        
        # Wait for prompt
        timeout = 10
        start = time.time()
        while not self.prompt_received and (time.time() - start) < timeout:
            time.sleep(0.01)
        
        if not self.prompt_received:
            _LOGGER.error("Did not receive prompt for SMS text")
            return False
        
        # Send message text with Ctrl-Z terminator
        _LOGGER.debug(f"Sending message text: {message}")
        message_data = message.encode('ascii', errors='ignore') + b'\x1A'
        self.write_data(message_data)
        
        # Wait for OK
        timeout = 30
        start = time.time()
        self.ok_received = False
        while not self.ok_received and (time.time() - start) < timeout:
            time.sleep(0.01)
        
        if self.ok_received:
            _LOGGER.info("SMS sent successfully")
            return True
        else:
            _LOGGER.error("SMS send timeout")
            return False
    
    def read_sms(self):
        """Read all SMS messages - simplified to avoid modem hangs."""
        _LOGGER.debug("Checking for SMS messages")
        
        # Skip SMS reading for now to prevent modem crashes
        # This is a known issue with some modems where AT+CMGL hangs
        # We'll implement SMS reception via unsolicited +CMTI notifications instead
        return []


class GSMSMSService:
    """Service that manages GSM SMS operations and Home Assistant integration."""
    
    def __init__(self, device_path, baud_speed=115200, scan_interval=30):
        """Initialize the GSM SMS service."""
        self.device_path = device_path
        self.device = device_path  # Alias for compatibility
        self.baud_speed = baud_speed
        self.scan_interval = scan_interval
        self.modem = None
        self.connected = False
        self.signal_strength = None
        
        # Home Assistant API configuration
        self.ha_url = "http://supervisor/core/api"
        self.ha_token = os.environ.get('SUPERVISOR_TOKEN', '')
        self.ha_headers = {
            'Authorization': f'Bearer {self.ha_token}',
            'Content-Type': 'application/json'
        }
        self.headers = self.ha_headers  # Alias for compatibility
        
        # Service registration status
        self.service_registered = False
        
        _LOGGER.info(f"Initialized with device: {self.device_path}, baud: {self.baud_speed}")

    def connect(self):
        """Connect to the GSM modem."""
        try:
            self.modem = GSMModem(self.device, self.baud_speed)
            
            if not self.modem.open():
                raise Exception("Failed to open modem")
            
            # Initialize modem
            self.modem.init_modem()
            
            # Get signal strength
            self.signal_strength = self.modem.get_signal_strength()
            
            self.connected = True
            _LOGGER.info("Successfully connected to modem")
            
            # Update HA sensor
            self.update_sensor("connected", {
                "signal_strength": self.signal_strength,
            })
            
            return True
            
        except Exception as e:
            _LOGGER.error(f"Failed to connect to modem: {e}")
            self.connected = False
            self.update_sensor("disconnected", {"error": str(e)})
            return False

    def disconnect(self):
        """Disconnect from the modem."""
        if self.modem:
            self.modem.close()
        self.connected = False
        _LOGGER.info("Disconnected from modem")

    def update_sensor(self, state, attributes=None):
        """Update Home Assistant sensor."""
        try:
            data = {
                "state": state,
                "attributes": attributes or {},
            }
            
            # Use state API - correct URL format
            url = f"{self.ha_url}/states/sensor.gsm_modem_status"
            response = requests.post(url, headers=self.headers, json=data, timeout=5)
            
            if response.status_code not in [200, 201]:
                _LOGGER.warning(f"Failed to update sensor: {response.status_code}")
                
        except Exception as e:
            _LOGGER.debug(f"Could not update sensor: {e}")

    def fire_event(self, event_type, event_data):
        """Fire a Home Assistant event."""
        try:
            url = f"{self.ha_url}/api/events/{event_type}"
            response = requests.post(url, headers=self.headers, json=event_data, timeout=5)
            
            if response.status_code not in [200, 201]:
                _LOGGER.warning(f"Failed to fire event: {response.status_code}")
                
        except Exception as e:
            _LOGGER.debug(f"Could not fire event: {e}")

    def send_sms_message(self, number, message):
        """Send an SMS message via the modem."""
        if not self.connected or not self.modem:
            _LOGGER.error("Cannot send SMS - modem not connected")
            return False
        
        try:
            result = self.modem.send_sms(number, message)
            if result:
                # Fire success event
                self.fire_event("legacy_gsm_sms_sent", {
                    "recipient": number,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "status": "success"
                })
            return result
        except Exception as e:
            _LOGGER.error(f"Error sending SMS: {e}")
            self.fire_event("legacy_gsm_sms_sent", {
                "recipient": number,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            })
            return False
    
    def check_sms(self):
        """Check for new SMS messages."""
        if not self.connected or not self.modem:
            return
        
        try:
            messages = self.modem.read_sms()
            
            for msg in messages:
                _LOGGER.info(f"Received SMS from {msg['Number']}: {msg['Text']}")
                
                # Fire event
                self.fire_event("legacy_gsm_sms_received", {
                    "sender": msg['Number'],
                    "message": msg['Text'],
                    "timestamp": datetime.now().isoformat(),
                })
                
        except Exception as e:
            _LOGGER.error(f"Error checking SMS: {e}")
    
    def register_service(self):
        """Display service setup instructions."""
        try:
            _LOGGER.info("=" * 60)
            _LOGGER.info("SMS Sending Service")
            _LOGGER.info("=" * 60)
            _LOGGER.info("")
            _LOGGER.info("Add this to your configuration.yaml:")
            _LOGGER.info("")
            _LOGGER.info("shell_command:")
            _LOGGER.info("  send_sms: >")
            _LOGGER.info("    echo '{\"action\":\"send_sms\",\"number\":\"{{ number }}\",\"message\":\"{{ message }}\"}' > /config/share/gsm_sms_queue.json")
            _LOGGER.info("")
            _LOGGER.info("Then reload shell_command and use in automations:")
            _LOGGER.info("")
            _LOGGER.info("  service: shell_command.send_sms")
            _LOGGER.info("  data:")
            _LOGGER.info("    number: '+1234567890'")
            _LOGGER.info("    message: 'Your message here'")
            _LOGGER.info("")
            _LOGGER.info("Note: /config/share is accessible as /share in the addon")
            _LOGGER.info("=" * 60)
            
            self.service_registered = True
            return True
                
        except Exception as e:
            _LOGGER.error(f"Error displaying instructions: {e}")
            return False
    
    def check_for_events(self):
        """Check for SMS send requests via file queue."""
        # Use file-based queue as primary method since event polling doesn't work in addons
        self.check_queue_fallback()
            
    def check_queue_fallback(self):
        """Fallback: Check file-based queue for SMS send requests."""
        # Use /share which is accessible from both HA and the addon
        queue_file = '/share/gsm_sms_queue.json'
        
        try:
            if os.path.exists(queue_file):
                _LOGGER.info(f"Queue file found: {queue_file}")
                
                with open(queue_file, 'r') as f:
                    content = f.read()
                    _LOGGER.debug(f"Queue file content: {content}")
                    command = json.loads(content)
                
                # Remove the file immediately
                os.remove(queue_file)
                _LOGGER.debug(f"Queue file removed")
                
                if command.get('action') == 'send_sms':
                    number = command.get('number')
                    message = command.get('message')
                    
                    if number and message:
                        _LOGGER.info(f"Processing queued SMS send request to {number}")
                        self.send_sms_message(number, message)
                    else:
                        _LOGGER.warning(f"Invalid SMS command - missing number or message. Got: {command}")
                else:
                    _LOGGER.warning(f"Invalid action in queue: {command.get('action')}")
                        
        except json.JSONDecodeError as e:
            _LOGGER.error(f"Invalid JSON in queue file: {e}")
            try:
                os.remove(queue_file)
            except:
                pass
        except Exception as e:
            _LOGGER.error(f"Error checking queue: {e}", exc_info=True)

    def run(self):
        """Run the service main loop."""
        _LOGGER.info("GSM SMS Service starting...")
        
        # Connect with retries
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            if self.connect():
                break
            
            retry_count += 1
            if retry_count < max_retries:
                _LOGGER.warning(f"Connection attempt {retry_count}/{max_retries} failed, retrying in 10 seconds...")
                time.sleep(10)
        
        if not self.connected:
            _LOGGER.error("Failed to connect to modem after all retries. Exiting.")
            return
        
        # Main loop
        _LOGGER.info(f"Entering main loop (scanning every {self.scan_interval} seconds)")
        
        try:
            last_check = 0
            while True:
                current_time = time.time()
                
                # Check for events and queue (fast check every second)
                self.check_for_events()
                
                # Check for incoming SMS (slower, based on scan_interval)
                if current_time - last_check >= self.scan_interval:
                    self.check_sms()
                    
                    # Update sensor
                    self.update_sensor("connected", {
                        "signal_strength": self.signal_strength,
                        "last_check": datetime.now().isoformat(),
                    })
                    
                    last_check = current_time
                
                # Sleep briefly
                time.sleep(1)
                
        except KeyboardInterrupt:
            _LOGGER.info("Service interrupted by user")
        except Exception as e:
            _LOGGER.error(f"Fatal error in main loop: {e}")
        finally:
            self.disconnect()


if __name__ == "__main__":
    # Get configuration from environment variables
    device = os.environ.get("DEVICE", "/dev/ttyUSB0")
    baud_speed = int(os.environ.get("BAUD_SPEED", "115200")) if os.environ.get("BAUD_SPEED", "0") != "0" else 115200
    scan_interval = int(os.environ.get("SCAN_INTERVAL", "30"))
    
    _LOGGER.info(f"Starting GSM SMS Service with device={device}, baud={baud_speed}, interval={scan_interval}")
    
    service = GSMSMSService(device, baud_speed, scan_interval)
    service.run()
