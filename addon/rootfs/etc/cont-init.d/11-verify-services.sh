#!/command/with-contenv bashio

# This script checks the service directories and reports their state
# for debugging purposes

bashio::log.info "===== SERVICE DIRECTORY VERIFICATION ====="

# Check for old-style S6 service directory
if [ -d "/etc/services.d/gsm_sms" ]; then
    bashio::log.warning "Found old S6 service directory: /etc/services.d/gsm_sms"
    ls -la /etc/services.d/gsm_sms
else
    bashio::log.info "No old S6 service directory found (good)"
fi

# Check for S6-overlay service directory
if [ -d "/etc/s6-overlay/s6-rc.d/gsm-sms" ]; then
    bashio::log.info "Found S6-overlay service directory: /etc/s6-overlay/s6-rc.d/gsm-sms"
    ls -la /etc/s6-overlay/s6-rc.d/gsm-sms
else
    bashio::log.error "Missing S6-overlay service directory!"
fi

# Check for service directories
bashio::log.info "Checking /run/s6/services:"
if [ -d "/run/s6/services" ]; then
    ls -la /run/s6/services
else
    bashio::log.warning "Directory /run/s6/services does not exist"
    mkdir -p /run/s6/services
    bashio::log.info "Created /run/s6/services directory"
fi

# Check for service directories
bashio::log.info "Checking /run/service:"
if [ -d "/run/service" ]; then
    ls -la /run/service
else
    bashio::log.warning "Directory /run/service does not exist"
    mkdir -p /run/service
    bashio::log.info "Created /run/service directory"
fi

bashio::log.info "===== END SERVICE DIRECTORY VERIFICATION ====="
