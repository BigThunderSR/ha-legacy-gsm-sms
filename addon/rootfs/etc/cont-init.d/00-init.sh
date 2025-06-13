#!/usr/bin/with-contenv bashio

# Create data directories
mkdir -p /data/gsm_sms

# Ensure environment variables are available
if [[ -z "${SUPERVISOR_TOKEN}" ]]; then
    bashio::log.warning "No SUPERVISOR_TOKEN set, some functionality may be limited"
fi

# Check if modem device exists
MODEM_DEVICE=$(bashio::config 'device')

if [ ! -e "${MODEM_DEVICE}" ]; then
    bashio::log.warning "GSM modem device not found: ${MODEM_DEVICE}"
    bashio::log.info "Available tty devices:"
    ls -la /dev/tty*
fi

# Set up runtime directory
mkdir -p /run/s6/container_environment
