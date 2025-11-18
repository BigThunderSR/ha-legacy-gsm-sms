#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -e

bashio::log.info "Starting GSM SMS Service..."

# Get configuration
DEVICE=$(bashio::config 'device')
BAUD_SPEED=$(bashio::config 'baud_speed')
SCAN_INTERVAL=$(bashio::config 'scan_interval')
LOG_LEVEL=$(bashio::config 'log_level')

bashio::log.info "Device: ${DEVICE}"
bashio::log.info "Baud Speed: ${BAUD_SPEED}"
bashio::log.info "Scan Interval: ${SCAN_INTERVAL}"
bashio::log.info "Log Level: ${LOG_LEVEL}"

# Export configuration as environment variables
export DEVICE
export BAUD_SPEED
export SCAN_INTERVAL
export LOG_LEVEL
export PYTHONUNBUFFERED=1

# Start the Python service
bashio::log.info "Executing Python service..."
exec python3 /usr/bin/gsm_sms_service.py < /dev/null
