#!/command/with-contenv bashio
exec >/proc/1/fd/1 2>/proc/1/fd/2

# Get log level from config
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "S6-RC initialization debug checker"

# List S6-RC directories
bashio::log.debug "S6-RC directories:"
ls -la /etc/s6-overlay/s6-rc.d/

# Check for the init-gsm-config service
bashio::log.debug "init-gsm-config service files:"
ls -la /etc/s6-overlay/s6-rc.d/init-gsm-config/

# Check for the gsm-sms service
bashio::log.debug "gsm-sms service files:"
ls -la /etc/s6-overlay/s6-rc.d/gsm-sms/

# Check user contents
bashio::log.debug "user/contents.d files:"
ls -la /etc/s6-overlay/s6-rc.d/user/contents.d/

# Check the gsm-services bundle
bashio::log.debug "gsm-services bundle:"
ls -la /etc/s6-overlay/s6-rc.d/gsm-services/

# Check bundle contents
bashio::log.debug "gsm-services contents.d files:"
ls -la /etc/s6-overlay/s6-rc.d/gsm-services/contents.d/

# Check the uncaught logs
if [ -f "/run/uncaught-logs/current" ]; then
    bashio::log.debug "=== UNCAUGHT LOGS ==="
    cat /run/uncaught-logs/current
    bashio::log.debug "=== END OF UNCAUGHT LOGS ==="
fi

# Check specific service failures
bashio::log.debug "=== S6-RC COMPILED DATABASE ==="
if [ -d "/run/s6/db" ]; then
    ls -la /run/s6/db
    bashio::log.debug "=== COMPILED SERVICE STATES ==="
    find /run/s6/db -type f -name "*gsm*" -exec cat {} \;
fi

# Create a visual marker to easily spot this information in logs
bashio::log.info "======= END OF S6-RC DEBUG INFO ======="
