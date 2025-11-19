#!/command/with-contenv bashio

# Get log level from config
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "Setting up S6-RC database for GSM services..."

# Report on S6-overlay version
S6_OVERLAY_VERSION=${S6_OVERLAY_VERSION:-"unknown"}
bashio::log.info "S6-overlay version: ${S6_OVERLAY_VERSION}"

# Make sure we don't have nested service directories
if [ -L "/etc/s6-overlay/s6-rc.d/gsm-sms/gsm-sms" ]; then
    bashio::log.warning "Removing nested symlink in gsm-sms source directory"
    rm -f /etc/s6-overlay/s6-rc.d/gsm-sms/gsm-sms
fi

# S6-overlay v3 needs these directories for compiled database
mkdir -p /run/s6-rc/servicedirs
mkdir -p /run/s6-rc/compiled
mkdir -p /run/s6-rc/source
mkdir -p /run/s6-rc/states
mkdir -p /etc/s6-overlay/scripts

# Create a complete S6 setup specifically for our service
bashio::log.info "Creating complete S6 service configuration"

# Create our primary service
mkdir -p /etc/s6-overlay/s6-rc.d/user/contents.d

# Clean directory before creating service symlinks
rm -f /run/s6-rc/servicedirs/gsm-services 2>/dev/null
rm -f /run/s6-rc/servicedirs/gsm-sms 2>/dev/null
rm -f /run/s6-rc/servicedirs/init-gsm-config 2>/dev/null
rm -f /run/s6-rc/servicedirs/gsm-bundle 2>/dev/null

# Create clean symlinks to the service directories
ln -sf /etc/s6-overlay/s6-rc.d/gsm-services /run/s6-rc/servicedirs/gsm-services
ln -sf /etc/s6-overlay/s6-rc.d/gsm-sms /run/s6-rc/servicedirs/gsm-sms
ln -sf /etc/s6-overlay/s6-rc.d/init-gsm-config /run/s6-rc/servicedirs/init-gsm-config
ln -sf /etc/s6-overlay/s6-rc.d/gsm-bundle /run/s6-rc/servicedirs/gsm-bundle

# Add our services to the user bundle
echo "gsm-bundle" > /etc/s6-overlay/s6-rc.d/user/contents.d/gsm-bundle

# Make sure we have correct permissions
chmod 755 /etc/s6-overlay/s6-rc.d/gsm-sms/run
chmod 755 /etc/s6-overlay/s6-rc.d/gsm-sms/finish
chmod 755 /etc/s6-overlay/s6-rc.d/init-gsm-config/up

bashio::log.info "S6-RC database setup complete"
