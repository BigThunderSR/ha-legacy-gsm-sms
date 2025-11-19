#!/command/with-contenv bashio

# Get log level from config
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "FALLBACK: S6 Direct Service Runner"

# Set up a trap for clean shutdown
trap 'bashio::log.info "Shutting down fallback service runner"; exit 0' SIGTERM SIGINT

# Create configuration from add-on options
bashio::log.info "Creating configuration..."
CONFIG_PATH=/data/options.json
MODEM_DEVICE=$(bashio::config 'device')
BAUD_SPEED=$(bashio::config 'baud_speed')
UNICODE=$(bashio::config 'unicode')
SCAN_INTERVAL=$(bashio::config 'scan_interval')
SERVICE_NAME=$(bashio::config 'service_name')
LOG_LEVEL=$(bashio::config 'log_level')

# Create configuration directory
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

# Verify file was created successfully
if [ -f "/data/gsm_sms/config.json" ]; then
    bashio::log.info "GSM SMS configuration created successfully"
else
    bashio::log.error "Failed to create GSM SMS configuration"
    exit 1
fi

# Write flag file to indicate services are up
mkdir -p /var/run/s6/etc
touch /var/run/s6/etc/services-up

# Start the Python service
bashio::log.info "Starting GSM SMS service directly..."
exec python3 /usr/bin/gsm_sms_service.py
