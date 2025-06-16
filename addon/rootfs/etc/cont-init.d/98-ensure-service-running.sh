#!/command/with-contenv bashio

# Check if service is running
SERVICE_RUNNING=false
if pgrep -f "/usr/bin/gsm_sms_service.py" > /dev/null; then
    SERVICE_RUNNING=true
fi

if [ "$SERVICE_RUNNING" = false ]; then
    # Try to run directly if S6 service isn't running
    bashio::log.warning "GSM SMS service not running via S6, launching directly..."
    
    # Notify service supervisor (if it exists)
    if [ -d "/var/run/s6/etc" ]; then
        touch /var/run/s6/etc/services-up
    fi

    # Execute service in the background
    python3 /usr/bin/gsm_sms_service.py &
    
    # Report startup
    bashio::log.info "GSM SMS service started directly"
else
    bashio::log.info "GSM SMS service already running via S6"
fi
