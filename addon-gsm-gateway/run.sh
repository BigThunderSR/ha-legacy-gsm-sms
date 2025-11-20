#!/usr/bin/with-contenv bashio

set -e

bashio::log.info "Starting SMS Gammu Gateway..."

# Check if configuration is valid
DEVICE_PATH=$(bashio::config 'device_path')
PIN=$(bashio::config 'pin')
PORT=$(bashio::config 'port')
USERNAME=$(bashio::config 'username')
PASSWORD=$(bashio::config 'password')

bashio::log.info "Device path: ${DEVICE_PATH}"
bashio::log.info "Port: ${PORT}"

# Check if device exists
if [ ! -c "${DEVICE_PATH}" ]; then
    bashio::log.warning "Device ${DEVICE_PATH} not found. Please check your GSM modem connection."
    bashio::log.info "Available tty devices:"
    ls -la /dev/tty* || true
fi

# Change to app directory
cd /app

# Start the application
bashio::log.info "Starting SMS Gateway on port ${PORT}..."
python3 run.py