#!/command/with-contenv bashio

# Create data directories
mkdir -p /data/gsm_sms

# Check if modem device exists
MODEM_DEVICE=$(bashio::config 'device')

if [ ! -e "${MODEM_DEVICE}" ]; then
    bashio::log.warning "GSM modem device not found: ${MODEM_DEVICE}"
    bashio::log.info "Available tty devices:"
    ls -la /dev/tty*
fi

bashio::log.info "Initialization complete"
