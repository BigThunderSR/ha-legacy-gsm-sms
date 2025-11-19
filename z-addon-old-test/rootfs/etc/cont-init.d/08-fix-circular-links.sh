#!/command/with-contenv bashio

# Get log level from config
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "S6 directory structure check and fix..."

# Check for circular symlinks in gsm-sms directory
if [ -L "/etc/s6-overlay/s6-rc.d/gsm-sms/gsm-sms" ]; then
    bashio::log.warning "Detected circular symlink in gsm-sms directory, removing"
    rm -f /etc/s6-overlay/s6-rc.d/gsm-sms/gsm-sms
fi

# Check other common locations for circular links
if [ -L "/run/s6/services/gsm-sms/gsm-sms" ]; then
    bashio::log.warning "Detected circular symlink in run services, removing"
    rm -f /run/s6/services/gsm-sms/gsm-sms
fi

if [ -L "/var/run/s6/services/gsm-sms/gsm-sms" ]; then
    bashio::log.warning "Detected circular symlink in var/run services, removing"
    rm -f /var/run/s6/services/gsm-sms/gsm-sms
fi

# Also check the servicedirs directory
if [ -d "/run/s6-rc/servicedirs" ]; then
    if [ -L "/run/s6-rc/servicedirs/gsm-sms/gsm-sms" ]; then
        bashio::log.warning "Detected circular symlink in servicedirs, removing"
        rm -f /run/s6-rc/servicedirs/gsm-sms/gsm-sms
    fi
fi

# Clean up the run directory to prevent conflicts
bashio::log.info "Cleaning up S6 run directories"
rm -rf /run/s6-rc/servicedirs/gsm-sms 2>/dev/null || true
rm -rf /run/s6/services/gsm-sms 2>/dev/null || true
rm -rf /var/run/s6/services/gsm-sms 2>/dev/null || true

# Recreate with proper symlinks (no nesting)
bashio::log.info "Recreating S6 service directories"
mkdir -p /run/s6-rc/servicedirs
mkdir -p /run/s6/services
mkdir -p /var/run/s6/services

# Create clean symlinks
ln -sf /etc/s6-overlay/s6-rc.d/gsm-sms /run/s6-rc/servicedirs/gsm-sms
ln -sf /etc/s6-overlay/s6-rc.d/gsm-sms /run/s6/services/gsm-sms
ln -sf /etc/s6-overlay/s6-rc.d/gsm-sms /var/run/s6/services/gsm-sms

# Create symlinks for init-gsm-config
ln -sf /etc/s6-overlay/s6-rc.d/init-gsm-config /run/s6-rc/servicedirs/init-gsm-config

# Add important S6-rc symlinks
mkdir -p /run/s6-rc/src
ln -sf /etc/s6-overlay/s6-rc.d /run/s6-rc/src/user

bashio::log.info "S6 directory structure fixed"
