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

# Check all uncaught logs
bashio::log.debug "=== UNCAUGHT LOGS ==="
if [ -f "/run/uncaught-logs/current" ]; then
    cat /run/uncaught-logs/current
elif [ -d "/run/uncaught-logs/" ]; then
    find /run/uncaught-logs -type f -exec cat {} \;
else
    echo "No uncaught logs found at /run/uncaught-logs/"
fi

# Also check service startup errors
if [ -d "/run/s6/services" ]; then
    for service_dir in /run/s6/services/*; do
        if [ -d "$service_dir" ] && [ -f "$service_dir/notification-fd" ]; then
            bashio::log.debug "=== SERVICE $(basename $service_dir) NOTIFICATION-FD ==="
            cat "$service_dir/notification-fd"
        fi
        if [ -d "$service_dir" ] && [ -f "$service_dir/event" ]; then
            bashio::log.debug "=== SERVICE $(basename $service_dir) EVENT ==="
            cat "$service_dir/event" || echo "No event file or empty"
        fi
    done
fi

if [ -d "/run/s6-rc" ]; then
    bashio::log.debug "=== S6-RC SERVICE STATES ==="
    find /run/s6-rc -name "state" -type f -exec cat {} \; 2>/dev/null || echo "No state files found"
fi
bashio::log.debug "=== END OF UNCAUGHT LOGS ==="

# Check specific service failures
bashio::log.debug "=== S6-RC COMPILED DATABASE ==="
if [ -d "/run/s6/db" ]; then
    ls -la /run/s6/db
    bashio::log.debug "=== COMPILED SERVICE STATES ==="
    find /run/s6/db -type f -name "*gsm*" -exec cat {} \;
fi

# Create a visual marker to easily spot this information in logs
bashio::log.info "======= END OF S6-RC DEBUG INFO ======="
