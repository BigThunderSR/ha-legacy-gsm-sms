#!/usr/bin/env python3
"""Simple CLI tool to send SMS via the modem service."""

import argparse
import json
import sys

def main():
    parser = argparse.ArgumentParser(description='Send SMS via GSM modem')
    parser.add_argument('--number', required=True, help='Phone number to send to')
    parser.add_argument('--message', required=True, help='Message text to send')
    args = parser.parse_args()
    
    # Write command to a queue file that the service monitors
    command = {
        'action': 'send_sms',
        'number': args.number,
        'message': args.message
    }
    
    try:
        with open('/tmp/gsm_sms_queue.json', 'w') as f:
            json.dump(command, f)
        print(f"SMS queued for {args.number}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
