#!/usr/bin/with-contenv bashio

# Setup sensor entities in Home Assistant

SERVICE_NAME=$(bashio::config 'service_name')

# Function to create sensor entities
create_sensor_entities() {
  local service_name=$1
  
  bashio::log.info "Setting up sensor entities..."
  
  # Signal strength sensor
  local entity="${service_name}_signal_strength"
  bashio::log.info "Creating sensor entity: $entity"
  
  local entity_json="{\"state\": \"unknown\", \"attributes\": {\"friendly_name\": \"GSM Signal Strength\", \"unit_of_measurement\": \"%\"}}"
  
  curl -s -X POST \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${entity_json}" \
    "http://supervisor/core/api/states/sensor.${entity}" \
    || bashio::log.warning "Failed to create sensor entity: ${entity}"
    
  # Network name sensor
  entity="${service_name}_network_name"
  bashio::log.info "Creating sensor entity: $entity"
  
  entity_json="{\"state\": \"unknown\", \"attributes\": {\"friendly_name\": \"GSM Network\"}}"
  
  curl -s -X POST \
    -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${entity_json}" \
    "http://supervisor/core/api/states/sensor.${entity}" \
    || bashio::log.warning "Failed to create sensor entity: ${entity}"
}

# Wait for Home Assistant API to be available
bashio::log.info "Waiting for Home Assistant API..."
sleep 10

# Create sensor entities
create_sensor_entities "${SERVICE_NAME}"

# Check if modem device exists
MODEM_DEVICE=$(bashio::config 'device')
if [ ! -e "$MODEM_DEVICE" ]; then
  bashio::log.warning "GSM modem device not found: $MODEM_DEVICE"
  bashio::log.info "Available devices:"
  ls -la /dev/tty*
fi
