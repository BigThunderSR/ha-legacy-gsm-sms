#!/usr/bin/env python3
"""Test script for Gammu configuration."""

import sys
import os
import json
import logging
import gammu

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

_LOGGER = logging.getLogger("test_gammu")

# Load config if available
config_file = '/data/gsm_sms/config.json'
device = '/dev/ttyUSB0'  # Default

try:
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            device = config_data.get('device', device)
            baud_speed = config_data.get('baud_speed', '0')
            _LOGGER.info(f"Loaded config: device={device}, baud_speed={baud_speed}")
    else:
        _LOGGER.info(f"No config file found at {config_file}, using defaults")

except Exception as e:
    _LOGGER.error(f"Error loading config: {e}")

# Try all possible configuration formats
_LOGGER.info("Testing Gammu configurations...")

# List all test configurations to try
test_configs = [
    # Config 1: Basic AT connection
    {
        "name": "Basic AT",
        "config": {
            "Device": device,
            "Connection": "at",
        }
    },
    # Config 2: AT serial connection
    {
        "name": "AT Serial",
        "config": {
            "Device": device,
            "Connection": "at19200",
        }
    },
    # Config 3: USB connection
    {
        "name": "USB",
        "config": {
            "Device": device,
            "Connection": "usb",
        }
    },
    # Config 4: Auto connection
    {
        "name": "Auto",
        "config": {
            "Device": device,
            "Connection": "auto",
        }
    }
]

# Try each configuration
success = False
for test in test_configs:
    try:
        _LOGGER.info(f"Trying configuration: {test['name']}")
        _LOGGER.info(f"Config: {test['config']}")
        
        # Initialize the state machine
        sm = gammu.StateMachine()
        sm.SetConfig(0, test['config'])
        
        # Try to initialize
        _LOGGER.info("Initializing connection...")
        sm.Init()
        
        # Try to get manufacturer
        _LOGGER.info("Getting manufacturer...")
        manufacturer = sm.GetManufacturer()
        _LOGGER.info(f"Manufacturer: {manufacturer}")
        
        # Try to get model
        _LOGGER.info("Getting model...")
        model = sm.GetModel()
        _LOGGER.info(f"Model: {model}")
        
        # Try to get IMEI
        _LOGGER.info("Getting IMEI...")
        imei = sm.GetIMEI()
        _LOGGER.info(f"IMEI: {imei}")
        
        # If we got here, we have a working configuration
        _LOGGER.info(f"SUCCESSFUL CONFIGURATION: {test['name']}")
        _LOGGER.info(f"Working config: {test['config']}")
        success = True
        
        # No need to try other configurations
        break
        
    except Exception as e:
        _LOGGER.error(f"Configuration {test['name']} failed: {e}")
        continue

# Report final status
if success:
    _LOGGER.info("Successfully found a working Gammu configuration!")
    sys.exit(0)
else:
    _LOGGER.error("Failed to find a working Gammu configuration.")
    sys.exit(1)
