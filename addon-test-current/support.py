"""
SMS Gammu Gateway - Support functions
Gammu integration functions for SMS operations and state machine management

Based on: https://github.com/pajikos/sms-gammu-gateway
Licensed under Apache License 2.0
"""

import sys
import os
import gammu
import time as time_module

# Cache for network type detection (avoid frequent disconnects)
_network_type_cache = {'type': None, 'timestamp': 0}
_NETWORK_TYPE_CACHE_SECONDS = 300  # Cache for 5 minutes


def init_state_machine(pin, device_path='/dev/ttyUSB0'):
    """Initialize gammu state machine with HA add-on config"""
    sm = gammu.StateMachine()

    # Create gammu config dynamically
    config_content = f"""[gammu]
device = {device_path}
connection = at
commtimeout = 10
"""

    # Write config to temporary file
    config_file = '/tmp/gammu.config'
    with open(config_file, 'w') as f:
        f.write(config_content)

    sm.ReadConfig(Filename=config_file)
    
    try:
        sm.Init()
        print(f"Successfully initialized gammu with device: {device_path}")
        
        # Try to check security status
        try:
            security_status = sm.GetSecurityStatus()
            print(f"SIM security status: {security_status}")
            
            if security_status == 'PIN':
                if pin is None or pin == '':
                    print("PIN is required but not provided.")
                    sys.exit(1)
                else:
                    sm.EnterSecurityCode('PIN', pin)
                    print("PIN entered successfully")
                    
        except Exception as e:
            print(f"Warning: Could not check SIM security status: {e}")
            
    except gammu.ERR_NOSIM:
        print("Warning: SIM card not accessible, but device is connected")
    except Exception as e:
        print(f"Error initializing device: {e}")
        print("Available devices:")
        import os
        try:
            devices = [d for d in os.listdir('/dev/') if d.startswith('tty')]
            for device in sorted(devices):
                print(f"  /dev/{device}")
        except:
            pass
        raise
        
    return sm


def retrieveAllSms(machine):
    """Retrieve all SMS messages from SIM/device memory"""
    try:
        status = machine.GetSMSStatus()
        allMultiPartSmsCount = status['SIMUsed'] + status['PhoneUsed'] + status['TemplatesUsed']

        allMultiPartSms = []
        start = True

        while len(allMultiPartSms) < allMultiPartSmsCount:
            if start:
                currentMultiPartSms = machine.GetNextSMS(Start=True, Folder=0)
                start = False
            else:
                currentMultiPartSms = machine.GetNextSMS(Location=currentMultiPartSms[0]['Location'], Folder=0)
            allMultiPartSms.append(currentMultiPartSms)

        allSms = gammu.LinkSMS(allMultiPartSms)

        results = []
        for sms in allSms:
            smsPart = sms[0]

            result = {
                "Date": str(smsPart['DateTime']),
                "Number": smsPart['Number'],
                "State": smsPart['State'],
                "Locations": [smsPart['Location'] for smsPart in sms],
            }

            decodedSms = gammu.DecodeSMS(sms)
            if decodedSms == None:
                result["Text"] = smsPart['Text']
            else:
                text = ""
                for entry in decodedSms['Entries']:
                    if entry['Buffer'] != None:
                        text += entry['Buffer']

                result["Text"] = text

            results.append(result)

        return results

    except Exception as e:
        print(f"Error retrieving SMS: {e}")
        raise  # Re-raise exception so track_gammu_operation can detect failure


def deleteSms(machine, sms):
    """Delete SMS by location"""
    try:
        list(map(lambda location: machine.DeleteSMS(Folder=0, Location=location), sms["Locations"]))
    except Exception as e:
        print(f"Error deleting SMS: {e}")


def encodeSms(smsinfo):
    """Encode SMS for sending"""
    return gammu.EncodeSMS(smsinfo)


def get_network_type(machine):
    """Get network type (2G/3G/4G/LTE) via AT commands
    
    Uses AT+CREG? command to retrieve Access Technology (AcT) parameter
    Returns human-readable network type string
    
    Note: Temporarily disconnects Gammu to send AT commands, then reconnects
    Results are cached for 5 minutes to minimize disconnects
    """
    import logging
    import serial
    import time
    import os
    
    # Check cache first
    global _network_type_cache
    current_time = time_module.time()
    if (_network_type_cache['type'] is not None and 
        current_time - _network_type_cache['timestamp'] < _NETWORK_TYPE_CACHE_SECONDS):
        return _network_type_cache['type']
    
    try:
        # Get the device path from Gammu config
        config = machine.GetConfig(0)
        device_path = config.get('Device', '')
        
        if not device_path:
            logging.warning("No device path found in Gammu config")
            return 'Unknown'
        
        # Resolve symlinks to get actual device
        if os.path.islink(device_path):
            device_path = os.path.realpath(device_path)
            logging.info(f"🔍 Resolved device path for AT commands: {device_path}")
        
        # Temporarily disconnect Gammu to free the serial port
        try:
            machine.Terminate()
            time.sleep(0.5)  # Give time for port to be released
            logging.info(f"🔍 Temporarily closed Gammu connection")
        except Exception as e:
            logging.warning(f"Could not terminate Gammu: {e}")
            return 'Unknown'
        
        # Open serial connection
        ser = None
        network_type = 'Unknown'
        try:
            ser = serial.Serial(
                port=device_path,
                baudrate=115200,
                timeout=2,
                write_timeout=2
            )
            
            # Small delay to let modem respond
            time.sleep(0.1)
            
            # Clear any existing data
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Use AT+CEREG? (EPS/LTE registration) - most reliable for LTE modems
            # Note: For optimal results, try CEREG first (LTE), then CGREG (GPRS), then CREG (CS)
            
            ser.write(b'AT+CEREG=2\r\n')
            time.sleep(0.2)
            response1 = ser.read_all().decode('utf-8', errors='ignore')
            logging.info(f"🔍 AT+CEREG=2 response: {response1.strip()}")
            
            ser.write(b'AT+CEREG?\r\n')
            time.sleep(0.2)
            response2 = ser.read_all().decode('utf-8', errors='ignore')
            logging.info(f"🔍 AT+CEREG? response: {response2.strip()}")
            
            for line in response2.split('\n'):
                if '+CEREG:' in line:
                    parts = line.split(':')[1].strip().split(',')
                    logging.info(f"🔍 Parsed CEREG parts: {parts}")
                    if len(parts) >= 5:
                        try:
                            act = int(parts[4].strip().strip('"'))
                            network_type = map_act_to_network_type(act)
                            logging.info(f"🔍 AT+CEREG? detected: {network_type} (AcT={act})")
                        except (ValueError, IndexError):
                            pass
            
            # Fallback: Try AT+CGREG? (GPRS) if CEREG didn't work
            if network_type == 'Unknown':
                ser.write(b'AT+CGREG=2\r\n')
                time.sleep(0.2)
                response3 = ser.read_all().decode('utf-8', errors='ignore')
                
                ser.write(b'AT+CGREG?\r\n')
                time.sleep(0.2)
                response4 = ser.read_all().decode('utf-8', errors='ignore')
                logging.info(f"🔍 AT+CGREG? response: {response4.strip()}")
                
                for line in response4.split('\n'):
                    if '+CGREG:' in line:
                        parts = line.split(':')[1].strip().split(',')
                        logging.info(f"🔍 Parsed CGREG parts: {parts}")
                        if len(parts) >= 5:
                            try:
                                act = int(parts[4].strip().strip('"'))
                                network_type = map_act_to_network_type(act)
                                logging.info(f"🔍 AT+CGREG? detected: {network_type} (AcT={act})")
                            except (ValueError, IndexError):
                                pass
            
            if network_type == 'Unknown':
                logging.warning("No AcT parameter found in AT+CEREG? or AT+CGREG? response")
            
        except Exception as e:
            logging.warning(f"Error sending AT commands: {e}")
            
        finally:
            if ser and ser.is_open:
                ser.close()
            time.sleep(0.3)
        
        # Reconnect Gammu
        try:
            machine.Init()
            logging.info(f"🔍 Reconnected Gammu successfully")
        except Exception as e:
            logging.error(f"Failed to reconnect Gammu: {e}")
        
        # Update cache
        _network_type_cache['type'] = network_type
        _network_type_cache['timestamp'] = current_time
        
        return network_type
        
    except Exception as e:
        logging.warning(f"Could not detect network type via AT commands: {e}")
        # Try to reconnect Gammu if it was disconnected
        try:
            machine.Init()
        except:
            pass
        return 'Unknown'


def map_act_to_network_type(act):
    """Map Access Technology value to human-readable network type"""
    act_map = {
        0: "2G (GSM)",
        1: "2G (GSM Compact)",
        2: "3G (UMTS)",
        3: "2.5G (EDGE)",
        4: "3G+ (HSPA)",
        5: "3G+ (HSUPA)",
        6: "3G+ (HSPA+)",
        7: "4G (LTE)",
        8: "2G (GSM-IoT)",
        9: "4G (NB-IoT)",
        10: "4G (LTE-5G)",
        11: "5G (NR)",
        12: "5G (NG-RAN)",
        13: "4G+5G (EN-DC)"
    }
    return act_map.get(act, f"Unknown (AcT={act})")


def get_network_type_at(machine):
    """Get network type using direct AT commands (if supported)
    
    This function attempts to use AT+CREG? to get Access Technology.
    Note: Requires modem that supports AT command passthrough.
    
    Access Technology values (3GPP TS 27.007):
    0 = GSM (2G)
    1 = GSM Compact (2G)
    2 = UTRAN (3G)
    3 = GSM w/EGPRS (EDGE/2.5G)
    4 = UTRAN w/HSDPA (3G+/HSPA)
    5 = UTRAN w/HSUPA (3G+/HSPA+)
    6 = UTRAN w/HSDPA and HSUPA (3G+/HSPA+)
    7 = E-UTRAN (LTE/4G)
    8 = EC-GSM-IoT (2G IoT)
    9 = E-UTRAN (NB-S1 mode) (NB-IoT)
    10 = E-UTRA connected to 5GCN (LTE anchored to 5G core)
    11 = NR connected to 5GCN (5G NR)
    12 = NG-RAN (5G)
    13 = E-UTRA-NR dual connectivity (EN-DC/4G+5G)
    """
    try:
        # Gammu doesn't provide direct AT command interface in standard API
        # This would require custom implementation or modem-specific backend
        # For now, return Unknown - can be enhanced with pyserial if needed
        return 'Unknown'
    except Exception as e:
        print(f"Warning: AT command network type detection failed: {e}")
        return 'Unknown'