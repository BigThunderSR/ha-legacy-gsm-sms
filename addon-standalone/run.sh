#!/usr/bin/with-contenv bashio
# ==============================================================================
# Start GSM SMS service
# ==============================================================================

# Get addon version from config
VERSION=$(bashio::addon.version)

# Get configuration using bashio
DEVICE=$(bashio::config 'device')
BAUD_SPEED=$(bashio::config 'baud_speed')
SCAN_INTERVAL=$(bashio::config 'scan_interval')
LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "=========================================="
bashio::log.info "Legacy GSM SMS Add-on v${VERSION}"
bashio::log.info "=========================================="
bashio::log.info "Configured device: ${DEVICE}"

# List available serial devices for debugging
bashio::log.info "Available devices:"
ls -la /dev/tty* 2>/dev/null | head -20 || bashio::log.warning "No tty devices found"
ls -la /dev/serial/by-id/ 2>/dev/null || bashio::log.warning "No /dev/serial/by-id/ directory"

# Try to find the actual device
ACTUAL_DEVICE="${DEVICE}"
if [ ! -e "${DEVICE}" ]; then
    bashio::log.warning "Configured device ${DEVICE} not found"
    
    # Try to find any ttyUSB device
    for dev in /dev/ttyUSB*; do
        if [ -e "$dev" ]; then
            ACTUAL_DEVICE="$dev"
            bashio::log.info "Found alternative device: ${ACTUAL_DEVICE}"
            break
        fi
    done
fi

# Export for Python script
export DEVICE="${ACTUAL_DEVICE}"
export BAUD_SPEED="${BAUD_SPEED}"
export SCAN_INTERVAL="${SCAN_INTERVAL}"
export LOG_LEVEL="${LOG_LEVEL}"

bashio::log.info "Using device: ${DEVICE}"
bashio::log.info "Baud Speed: ${BAUD_SPEED}"
bashio::log.info "Scan Interval: ${SCAN_INTERVAL}"

# Run the Python service
exec python3 /usr/bin/gsm_sms_service.py
