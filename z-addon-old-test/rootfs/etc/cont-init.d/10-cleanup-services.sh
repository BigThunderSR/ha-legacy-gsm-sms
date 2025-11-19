#!/command/with-contenv bashio

# This script cleans up any duplicate service directories
# to prevent conflicts between traditional S6 and S6-overlay

bashio::log.info "Cleaning up service directories..."

# Remove the old service directory if it exists
if [ -d "/etc/services.d/gsm_sms" ]; then
    bashio::log.info "Removing duplicate service directory: /etc/services.d/gsm_sms"
    rm -rf /etc/services.d/gsm_sms
fi

# Make sure our S6-overlay service has correct permissions
if [ -f "/etc/s6-overlay/s6-rc.d/gsm-sms/run" ]; then
    bashio::log.debug "Setting correct permissions for S6-overlay service"
    chmod a+x /etc/s6-overlay/s6-rc.d/gsm-sms/run
    chmod a+x /etc/s6-overlay/s6-rc.d/gsm-sms/finish
fi

if [ -f "/etc/s6-overlay/s6-rc.d/init-gsm-config/up" ]; then
    chmod a+x /etc/s6-overlay/s6-rc.d/init-gsm-config/up
fi

bashio::log.info "Service directory cleanup completed"
