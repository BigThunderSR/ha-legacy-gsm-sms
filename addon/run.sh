#!/usr/bin/with-contenv bashio

CONFIG_PATH=/data/options.json
MODEM_DEVICE=$(bashio::config 'device')
BAUD_SPEED=$(bashio::config 'baud_speed')
UNICODE=$(bashio::config 'unicode')
SCAN_INTERVAL=$(bashio::config 'scan_interval')
SERVICE_NAME=$(bashio::config 'service_name')

# Set up the GSM SMS service directly, without using the HACS integration
bashio::log.info "Setting up Legacy GSM SMS service..."

# Create configuration for the SMS service
mkdir -p /data/gsm_sms
cat > /data/gsm_sms/config.json << EOL
{
  "device": "${MODEM_DEVICE}",
  "baud_speed": "${BAUD_SPEED}",
  "unicode": ${UNICODE},
  "scan_interval": ${SCAN_INTERVAL},
  "service_name": "${SERVICE_NAME}"
}
EOL

# Check if modem device exists
if [ ! -e "$MODEM_DEVICE" ]; then
  bashio::log.warning "GSM modem device not found: $MODEM_DEVICE"
  bashio::log.info "Available devices:"
  ls -la /dev/tty*
fi

bashio::log.info "Legacy GSM SMS addon started"
bashio::log.info "Modem device: $MODEM_DEVICE"
bashio::log.info "Baud speed: $BAUD_SPEED"
bashio::log.info "Unicode: $UNICODE"
bashio::log.info "Scan interval: $SCAN_INTERVAL"
bashio::log.info "Service name: $SERVICE_NAME"

# Create sensor entities
bashio::log.info "Setting up sensor entities..."
for entity in "${SERVICE_NAME}_signal_strength" "${SERVICE_NAME}_network_name"; do
  bashio::log.info "Creating sensor entity: $entity"
  
  # Determine friendly name and unit based on entity type
  if [[ "$entity" == *"signal_strength"* ]]; then
    FRIENDLY_NAME="GSM Signal Strength"
    UNIT="%"
  else
    FRIENDLY_NAME="GSM Network"
    UNIT=""
  fi
  
  # Create entity JSON
  if [[ -n "$UNIT" ]]; then
    ENTITY_JSON="{\"state\": \"unknown\", \"attributes\": {\"friendly_name\": \"$FRIENDLY_NAME\", \"unit_of_measurement\": \"$UNIT\"}}"
  else
    ENTITY_JSON="{\"state\": \"unknown\", \"attributes\": {\"friendly_name\": \"$FRIENDLY_NAME\"}}"
  fi
  
  # Send request to Home Assistant API
  curl -s -X POST \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$ENTITY_JSON" \
    "http://supervisor/core/api/states/sensor.${entity}" \
    || bashio::log.warning "Failed to create sensor entity: ${entity}"
done

# Start the GSM SMS service
bashio::log.info "Starting GSM SMS service..."
python3 /app/gsm_sms_service.py
