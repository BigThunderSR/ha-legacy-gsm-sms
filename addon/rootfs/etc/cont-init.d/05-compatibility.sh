#!/command/with-contenv bashio

# This script creates compatibility symlinks if needed
bashio::log.info "Setting up compatibility symlinks..."

# Create services.d directory if it doesn't exist
if [ ! -d "/run/service" ]; then
    bashio::log.info "Creating /run/service directory"
    mkdir -p /run/service
fi

# Create s6 services directory if it doesn't exist
if [ ! -d "/run/s6/services" ]; then
    bashio::log.info "Creating /run/s6/services directory"
    mkdir -p /run/s6/services
fi

# Create symlink for compatibility
if [ ! -L "/run/s6/services/gsm-sms" ]; then
    ln -s /etc/s6-overlay/s6-rc.d/gsm-sms /run/s6/services/gsm-sms
    bashio::log.info "Created symlink for gsm-sms service"
fi

bashio::log.info "Compatibility symlinks complete"
