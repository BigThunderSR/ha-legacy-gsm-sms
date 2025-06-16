#!/usr/bin/with-contenv bashio
# ==============================================================================
# Start the GSM SMS service (fallback direct entry point)
# ==============================================================================
bashio::log.info "Starting GSM SMS service using run.sh..."

# First, let's make sure our directories exist
mkdir -p /run/service
mkdir -p /run/s6/services

# Debug information about S6 environment
if [ "$LOG_LEVEL" == "debug" ]; then
  bashio::log.debug "S6 Runtime Environment:"
  bashio::log.debug "S6_BEHAVIOUR_IF_STAGE2_FAILS=${S6_BEHAVIOUR_IF_STAGE2_FAILS}"
  bashio::log.debug "S6_CMD_WAIT_FOR_SERVICES=${S6_CMD_WAIT_FOR_SERVICES}"
  
  # Check for required directories
  bashio::log.debug "Checking for S6 directories:"
  find /etc/s6-overlay -type d | sort | bashio::log.debug
fi

# Create config if needed
bashio::log.info "Setting up configuration..."
CONFIG_PATH=/data/options.json
MODEM_DEVICE=$(bashio::config 'device')
BAUD_SPEED=$(bashio::config 'baud_speed')
UNICODE=$(bashio::config 'unicode')
SCAN_INTERVAL=$(bashio::config 'scan_interval')
SERVICE_NAME=$(bashio::config 'service_name')
LOG_LEVEL=$(bashio::config 'log_level')

# Create configuration for the SMS service
mkdir -p /data/gsm_sms
cat > /data/gsm_sms/config.json << EOL
{
  "device": "${MODEM_DEVICE}",
  "baud_speed": "${BAUD_SPEED}",
  "unicode": ${UNICODE},
  "scan_interval": ${SCAN_INTERVAL},
  "service_name": "${SERVICE_NAME}",
  "log_level": "${LOG_LEVEL}"
}
EOL

# Set up logging
bashio::log.level "${LOG_LEVEL}"

# Start the python service as a foreground process
bashio::log.info "Starting GSM SMS Python service..."
exec python3 /usr/bin/gsm_sms_service.py
