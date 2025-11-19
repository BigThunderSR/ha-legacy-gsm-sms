#!/usr/bin/with-contenv bashio
# ==============================================================================
# Start the GSM SMS service (fallback direct entry point)
# ==============================================================================
bashio::log.info "Starting GSM SMS service using run.sh..."

# Get log level
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

# Try two approaches to start the service:
# 1. Use S6-overlay (preferred)
# 2. Direct execution (fallback)

# Set up trap for proper shutdown
trap 'bashio::log.info "Received shutdown signal, stopping service..."; exit 0' TERM INT

# Create all required runtime directories
mkdir -p /run/service
mkdir -p /run/s6/services
mkdir -p /var/run/s6/services
mkdir -p /run/s6-rc/servicedirs
mkdir -p /var/run/s6/etc
mkdir -p /data/gsm_sms

# Debug information
bashio::log.debug "==== ENVIRONMENT INFORMATION ===="
bashio::log.debug "Current directory: $(pwd)"
bashio::log.debug "S6_BEHAVIOUR_IF_STAGE2_FAILS=${S6_BEHAVIOUR_IF_STAGE2_FAILS}"
bashio::log.debug "S6_CMD_WAIT_FOR_SERVICES=${S6_CMD_WAIT_FOR_SERVICES}"
bashio::log.debug "Checking S6 directories:"
find /etc/s6-overlay -type d | sort | bashio::log.debug
bashio::log.debug "==== END ENVIRONMENT INFORMATION ===="

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

# Make sure init scripts are executed (in case S6 doesn't run them)
if [ -d "/etc/cont-init.d" ]; then
    for init in /etc/cont-init.d/*.sh; do
        if [ -f "$init" ]; then
            bashio::log.info "Running initialization script: $init"
            $init
        fi
    done
fi

# Signal to Home Assistant that services are up
mkdir -p /var/run/s6/etc
touch /var/run/s6/etc/services-up

# Try to exec into S6 supervisor if available
if command -v s6-svscan > /dev/null && [ -d "/etc/s6-overlay/s6-rc.d" ]; then
    bashio::log.info "Starting with S6 supervisor..."
    exec s6-svscan -t0 /run/service
else
    # Fallback to directly starting the Python service
    bashio::log.warning "S6 supervisor not available, starting service directly..."
    exec python3 /usr/bin/gsm_sms_service.py
fi
