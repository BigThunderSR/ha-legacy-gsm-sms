#!/command/with-contenv bashio

# Get log level from config
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "Cleaning up legacy service bundle configurations..."

# Remove any old symlinks that might be causing conflicts
if [ -d "/run/s6/legacy-services" ]; then
    bashio::log.info "Removing legacy service directory symlinks"
    rm -rf /run/s6/legacy-services
fi

# S6-overlay v3 needs these directories
bashio::log.info "Ensuring S6 runtime directories exist"
mkdir -p /run/s6/services
mkdir -p /run/service

# Create symlinks to the correct service directories
if [ -d "/etc/s6-overlay/s6-rc.d/gsm-sms" ]; then
    bashio::log.info "Creating symlinks for gsm-sms service"
    ln -sf /etc/s6-overlay/s6-rc.d/gsm-sms /run/s6/services/gsm-sms
fi

bashio::log.info "Legacy service cleanup complete"
