#!/usr/bin/with-contenv bashio
# ==============================================================================
# Start GSM SMS service
# ==============================================================================

# Get configuration using bashio
DEVICE=$(bashio::config 'device')
BAUD_SPEED=$(bashio::config 'baud_speed')
SCAN_INTERVAL=$(bashio::config 'scan_interval')
LOG_LEVEL=$(bashio::config 'log_level')

# Export for Python script
export DEVICE="${DEVICE}"
export BAUD_SPEED="${BAUD_SPEED}"
export SCAN_INTERVAL="${SCAN_INTERVAL}"
export LOG_LEVEL="${LOG_LEVEL}"

bashio::log.info "Starting GSM SMS Service..."
bashio::log.info "Device: ${DEVICE}"
bashio::log.info "Baud Speed: ${BAUD_SPEED}"
bashio::log.info "Scan Interval: ${SCAN_INTERVAL}"

# Check if device exists
if bashio::fs.file_exists "${DEVICE}"; then
    bashio::log.info "Device ${DEVICE} found"
else
    bashio::log.warning "Device ${DEVICE} not found, waiting..."
fi

# Run the Python service
exec python3 /usr/bin/gsm_sms_service.py
