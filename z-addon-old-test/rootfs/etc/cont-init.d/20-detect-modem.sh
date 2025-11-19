#!/command/with-contenv bashio
# Detect GSM modem devices

bashio::log.info "Detecting GSM modem devices..."

# Array of potential modem devices to check
DEVICE_PATTERNS=(
    "/dev/ttyUSB*"
    "/dev/ttyACM*"
    "/dev/serial/by-id/*"
)

# Get the configured device from options
CONFIGURED_DEVICE=$(bashio::config 'device')
bashio::log.info "Configured device: ${CONFIGURED_DEVICE}"

# Check if configured device exists
if [ -e "$CONFIGURED_DEVICE" ]; then
    bashio::log.info "Configured device exists: ${CONFIGURED_DEVICE}"
else
    bashio::log.warning "Configured device does not exist: ${CONFIGURED_DEVICE}"
    bashio::log.info "Looking for alternative devices..."
    
    # Find all potential modem devices
    FOUND_DEVICES=()
    
    for pattern in "${DEVICE_PATTERNS[@]}"; do
        for device in $pattern; do
            if [ -e "$device" ]; then
                FOUND_DEVICES+=("$device")
            fi
        done
    done
    
    # Log found devices
    if [ ${#FOUND_DEVICES[@]} -gt 0 ]; then
        bashio::log.info "Found potential modem devices:"
        for device in "${FOUND_DEVICES[@]}"; do
            bashio::log.info " - ${device}"
        done
        
        # Update the config to use the first found device
        mkdir -p /data/gsm_sms
        CONFIG_FILE="/data/gsm_sms/config.json"
        
        if [ -f "$CONFIG_FILE" ]; then
            # Read current config
            UNICODE=$(jq -r '.unicode' "$CONFIG_FILE")
            SCAN_INTERVAL=$(jq -r '.scan_interval' "$CONFIG_FILE")
            SERVICE_NAME=$(jq -r '.service_name' "$CONFIG_FILE")
            LOG_LEVEL=$(jq -r '.log_level' "$CONFIG_FILE")
            BAUD_SPEED=$(jq -r '.baud_speed' "$CONFIG_FILE")
            
            # Update device in config
            NEW_DEVICE="${FOUND_DEVICES[0]}"
            bashio::log.info "Updating configuration to use device: ${NEW_DEVICE}"
            
            # Create updated config
            cat > "$CONFIG_FILE" << EOL
{
  "device": "${NEW_DEVICE}",
  "baud_speed": "${BAUD_SPEED}",
  "unicode": ${UNICODE},
  "scan_interval": ${SCAN_INTERVAL},
  "service_name": "${SERVICE_NAME}",
  "log_level": "${LOG_LEVEL}"
}
EOL
        else
            bashio::log.warning "Config file not found, cannot update device"
        fi
    else
        bashio::log.error "No GSM modem devices found!"
    fi
fi

# List all USB devices for debugging
bashio::log.debug "Listing USB devices:"
lsusb | bashio::log.debug
