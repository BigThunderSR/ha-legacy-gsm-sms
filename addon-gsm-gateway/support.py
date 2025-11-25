"""
SMS Gammu Gateway - Support functions
Gammu integration functions for SMS operations and state machine management

Based on: https://github.com/pajikos/sms-gammu-gateway
Licensed under Apache License 2.0
"""

import sys
import os
import gammu


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
    """
    try:
        # Try to get network registration with access technology
        # AT+CREG=2 enables extended format with <AcT>
        # Format: +CREG: <n>,<stat>[,<lac>,<ci>[,<AcT>]]
        
        # Some modems might support this via custom AT commands
        # Since Gammu doesn't expose direct AT command interface by default,
        # we'll try to infer from available data or use fallback
        
        # Try to read network info - some implementations include GPRS state
        network_info = machine.GetNetworkInfo()
        
        # Check if GPRS/Packet data fields are available (modem-dependent)
        gprs_state = network_info.get('GPRS', '')
        packet_state = network_info.get('PacketNetworkState', '')
        
        # Map GPRS states to network types (basic heuristic)
        if gprs_state == 'Attached' or packet_state:
            # If GPRS is attached, we're at least on 2G/2.5G
            # More sophisticated detection would require AT commands
            return 'Unknown'  # Conservative default
        
        return 'Unknown'
        
    except Exception as e:
        print(f"Warning: Could not detect network type: {e}")
        return 'Unknown'


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