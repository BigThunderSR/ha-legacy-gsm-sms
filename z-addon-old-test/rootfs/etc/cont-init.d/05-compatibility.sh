#!/command/with-contenv bashio

# This script creates compatibility symlinks if needed
bashio::log.info "Setting up compatibility symlinks..."

# Create all required S6 directories
mkdir -p /run/service
mkdir -p /run/s6/services
mkdir -p /var/run/s6/services
mkdir -p /run/s6/legacy-services
mkdir -p /run/s6-rc/servicedirs
mkdir -p /run/s6-rc/compiled
mkdir -p /run/s6-rc/source
mkdir -p /var/run/s6/etc
mkdir -p /etc/s6-overlay/scripts

# Create symlink for compatibility
if [ ! -L "/run/s6/services/gsm-sms" ]; then
    ln -s /etc/s6-overlay/s6-rc.d/gsm-sms /run/s6/services/gsm-sms
    bashio::log.info "Created symlink for gsm-sms service"
fi

bashio::log.info "Compatibility symlinks complete"
