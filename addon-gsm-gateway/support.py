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
_network_type_cache_seconds = 300  # Default: Cache for 5 minutes (configurable)


def set_network_type_cache_duration(seconds):
    """Set the cache duration for network type detection"""
    global _network_type_cache_seconds
    _network_type_cache_seconds = seconds


def invalidate_network_type_cache():
    """Invalidate the network type cache (call when modem reconnects)"""
    global _network_type_cache
    _network_type_cache['type'] = None
    _network_type_cache['timestamp'] = 0


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

            # Try to decode SMS - this may fail for MMS notifications or corrupted messages
            try:
                decodedSms = gammu.DecodeSMS(sms)
                if decodedSms == None:
                    # DecodeSMS returned None - use raw text from SMS part
                    result["Text"] = smsPart.get('Text', '')
                else:
                    # Successfully decoded - concatenate all text entries
                    text = ""
                    for entry in decodedSms['Entries']:
                        if entry.get('Buffer') is not None:
                            text += entry['Buffer']
                    result["Text"] = text if text else smsPart.get('Text', '')

            except UnicodeDecodeError as e:
                # MMS notification or binary message that can't be decoded as UTF-8
                print(f"Warning: Cannot decode SMS as UTF-8 (probably MMS notification): {e}")
                # Try to get raw text, but handle potential binary data safely
                try:
                    raw_text = smsPart.get('Text', '')
                    # If Text is bytes, try to decode with error handling
                    if isinstance(raw_text, bytes):
                        result["Text"] = raw_text.decode('utf-8', errors='replace')
                    else:
                        result["Text"] = str(raw_text) if raw_text else '[MMS or binary message]'
                except Exception:
                    result["Text"] = '[MMS or binary message - cannot display]'

            except Exception as e:
                # Any other decoding error (corrupted SMS, unknown format, etc.)
                print(f"Warning: Error decoding SMS: {e}")
                # Fallback to raw text with safe handling
                try:
                    raw_text = smsPart.get('Text', '')
                    if isinstance(raw_text, bytes):
                        result["Text"] = raw_text.decode('utf-8', errors='replace')
                    else:
                        result["Text"] = str(raw_text) if raw_text else '[Decoding error]'
                except Exception:
                    result["Text"] = '[Message decoding failed]'

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
    
    Uses AT+CEREG? command to retrieve Access Technology (AcT) parameter
    Returns human-readable network type string
    
    Note: Temporarily disconnects Gammu to send AT commands, then reconnects
    Results are cached for 5 minutes to minimize disconnects
    """
    import logging
    import serial
    import time
    import os
    
    # Check cache first
    # If _network_type_cache_seconds <= 0, cache never expires (only on modem reconnect)
    # Otherwise, cache expires after the configured duration
    global _network_type_cache, _network_type_cache_seconds
    current_time = time_module.time()
    if _network_type_cache['type'] is not None:
        # Cache exists - check if it's still valid
        if _network_type_cache_seconds <= 0:
            # Cache never expires (reconnect-only mode)
            return _network_type_cache['type']
        cache_age = current_time - _network_type_cache['timestamp']
        if cache_age < _network_type_cache_seconds:
            # Cache hasn't expired yet
            return _network_type_cache['type']
    
    try:
        # Get the device path from Gammu config
        config = machine.GetConfig(0)
        device_path = config.get('Device', '')
        
        if not device_path:
            return 'Unknown'
        
        # Resolve symlinks to get actual device
        if os.path.islink(device_path):
            device_path = os.path.realpath(device_path)
        
        # Temporarily disconnect Gammu to free the serial port
        try:
            machine.Terminate()
            time.sleep(0.5)
        except Exception:
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
            
            time.sleep(0.1)
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # Use AT+CEREG? (EPS/LTE registration) - most reliable for LTE modems
            ser.write(b'AT+CEREG=2\r\n')
            time.sleep(0.2)
            ser.read_all()
            
            ser.write(b'AT+CEREG?\r\n')
            time.sleep(0.2)
            response = ser.read_all().decode('utf-8', errors='ignore')
            
            for line in response.split('\n'):
                if '+CEREG:' in line:
                    parts = line.split(':')[1].strip().split(',')
                    if len(parts) >= 5:
                        try:
                            act = int(parts[4].strip().strip('"'))
                            network_type = map_act_to_network_type(act)
                        except (ValueError, IndexError):
                            pass
            
            # Fallback: Try AT+CGREG? (GPRS) if CEREG didn't work
            if network_type == 'Unknown':
                ser.write(b'AT+CGREG=2\r\n')
                time.sleep(0.2)
                ser.read_all()
                
                ser.write(b'AT+CGREG?\r\n')
                time.sleep(0.2)
                response = ser.read_all().decode('utf-8', errors='ignore')
                
                for line in response.split('\n'):
                    if '+CGREG:' in line:
                        parts = line.split(':')[1].strip().split(',')
                        if len(parts) >= 5:
                            try:
                                act = int(parts[4].strip().strip('"'))
                                network_type = map_act_to_network_type(act)
                            except (ValueError, IndexError):
                                pass
            
        except Exception:
            pass
            
        finally:
            if ser and ser.is_open:
                ser.close()
            time.sleep(0.3)
        
        # Reconnect Gammu
        try:
            machine.Init()
        except Exception:
            pass
        
        # Update cache
        _network_type_cache['type'] = network_type
        _network_type_cache['timestamp'] = current_time
        
        return network_type
        
    except Exception:
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