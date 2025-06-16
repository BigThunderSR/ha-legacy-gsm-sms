#!/command/with-contenv bashio

# Get log level from config
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "Setting up S6-RC database for GSM services..."

# S6-overlay v3 needs to know about our bundle
mkdir -p /run/s6-rc/servicedirs
mkdir -p /run/s6-rc/states

if [ -d "/etc/s6-overlay/s6-rc.d/gsm-services" ]; then
    bashio::log.info "Found GSM services bundle, setting up"
    
    if [ ! -L "/run/s6-rc/servicedirs/gsm-services" ]; then
        ln -sf /etc/s6-overlay/s6-rc.d/gsm-services /run/s6-rc/servicedirs/gsm-services
        bashio::log.info "Created symlink for gsm-services bundle"
    fi
    
    if [ -d "/etc/s6-overlay/s6-rc.d/gsm-sms" ] && [ ! -L "/run/s6-rc/servicedirs/gsm-sms" ]; then
        ln -sf /etc/s6-overlay/s6-rc.d/gsm-sms /run/s6-rc/servicedirs/gsm-sms
        bashio::log.info "Created symlink for gsm-sms service"
    fi
    
    if [ -d "/etc/s6-overlay/s6-rc.d/init-gsm-config" ] && [ ! -L "/run/s6-rc/servicedirs/init-gsm-config" ]; then
        ln -sf /etc/s6-overlay/s6-rc.d/init-gsm-config /run/s6-rc/servicedirs/init-gsm-config
        bashio::log.info "Created symlink for init-gsm-config service"
    fi
else
    bashio::log.warning "GSM services bundle not found!"
fi

bashio::log.info "S6-RC database setup complete"
