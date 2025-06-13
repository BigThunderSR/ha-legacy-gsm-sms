#!/bin/bash
# Script to send SMS messages directly from the command line

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 PHONE_NUMBER MESSAGE"
  echo "Example: $0 +1234567890 'Hello from Home Assistant!'"
  exit 1
fi

PHONE_NUMBER="$1"
MESSAGE="$2"
CONFIG_FILE="/data/gsm_sms/config.json"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: Config file not found!"
  exit 1
fi

# Extract device and baud speed from config
DEVICE=$(jq -r '.device' "$CONFIG_FILE")
BAUD_SPEED=$(jq -r '.baud_speed' "$CONFIG_FILE")
SERVICE_NAME=$(jq -r '.service_name' "$CONFIG_FILE")

if [ -z "$DEVICE" ]; then
  echo "Error: Device not configured!"
  exit 1
fi

echo "Sending SMS to $PHONE_NUMBER using device $DEVICE"
echo "Message: $MESSAGE"

# Use curl to call the Home Assistant service
curl -s -X POST \
  -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"$MESSAGE\", \"target\": \"$PHONE_NUMBER\"}" \
  "http://supervisor/core/api/services/notify/$SERVICE_NAME"

echo "SMS sent!"
