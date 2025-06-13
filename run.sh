#!/usr/bin/with-contenv bashio

CONFIG_PATH=/data/options.json
MODEM_DEVICE=$(bashio::config 'device')
BAUD_SPEED=$(bashio::config 'baud_speed')
UNICODE=$(bashio::config 'unicode')
SCAN_INTERVAL=$(bashio::config 'scan_interval')

# Create required directories
mkdir -p /config/custom_components/legacy_gsm_sms
mkdir -p /config/custom_components/legacy_gsm_sms/brand

# Copy the integration files to the Home Assistant config directory
cp /app/*.py /config/custom_components/legacy_gsm_sms/

# Create or update manifest.json
cat > /config/custom_components/legacy_gsm_sms/manifest.json << EOL
{
  "domain": "legacy_gsm_sms",
  "name": "Legacy GSM SMS notifications via GSM-modem",
  "codeowners": ["@BigThunderSR", "@ocalvo"],
  "config_flow": true,
  "documentation": "https://github.com/BigThunderSR/ha-legacy-gsm-sms",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/BigThunderSR/ha-legacy-gsm-sms/issues",
  "loggers": ["gammu"],
  "requirements": ["python-gammu==3.2.4"],
  "version": "1.0.0"
}
EOL

# Copy brand icon and logo if they exist
if [ -d "/app/brand" ]; then
  cp -R /app/brand /config/custom_components/legacy_gsm_sms/
fi

# Check if modem device exists
if [ ! -e "$MODEM_DEVICE" ]; then
  bashio::log.warning "GSM modem device not found: $MODEM_DEVICE"
  bashio::log.info "Available devices:"
  ls -la /dev/tty*
fi

bashio::log.info "Legacy GSM SMS addon started"
bashio::log.info "Modem device: $MODEM_DEVICE"
bashio::log.info "Baud speed: $BAUD_SPEED"
bashio::log.info "Unicode: $UNICODE"
bashio::log.info "Scan interval: $SCAN_INTERVAL"

# Keep the addon running
while true; do
  sleep 30
  # Check if modem is still accessible
  if [ -e "$MODEM_DEVICE" ]; then
    bashio::log.debug "Modem device is accessible: $MODEM_DEVICE"
  else
    bashio::log.warning "Modem device not found: $MODEM_DEVICE"
  fi
done
