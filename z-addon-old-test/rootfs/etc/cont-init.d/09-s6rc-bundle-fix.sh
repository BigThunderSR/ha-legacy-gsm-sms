#!/command/with-contenv bashio

# Get log level from config
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "Running S6-RC bundle connection fix..."

# Create an S6-rc bundle file
S6_RC_BUNDLE="/etc/s6-overlay/s6-rc.d/gsm-bundle"
mkdir -p "${S6_RC_BUNDLE}/contents.d"

# Create the bundle type file
echo "bundle" > "${S6_RC_BUNDLE}/type"

# Clean out any existing content files to avoid duplication
rm -f "${S6_RC_BUNDLE}/contents.d/*" 2>/dev/null

# Add our services to the bundle
echo "gsm-sms" > "${S6_RC_BUNDLE}/contents.d/gsm-sms"
echo "init-gsm-config" > "${S6_RC_BUNDLE}/contents.d/init-gsm-config"

# Make sure this bundle is loaded at startup
mkdir -p "/etc/s6-overlay/s6-rc.d/user/contents.d"
echo "gsm-bundle" > "/etc/s6-overlay/s6-rc.d/user/contents.d/gsm-bundle"

# Remove legacy bundles to avoid conflicts
rm -f "/etc/s6-overlay/s6-rc.d/user/contents.d/gsm-sms" 2>/dev/null
rm -f "/etc/s6-overlay/s6-rc.d/user/contents.d/gsm-services" 2>/dev/null
rm -f "/etc/s6-overlay/s6-rc.d/user/contents.d/init-gsm-config" 2>/dev/null

# Make sure there's a proper "up" script for the oneshot service
if [ ! -f "/etc/s6-overlay/s6-rc.d/init-gsm-config/up" ]; then
    bashio::log.error "The 'up' script is missing for init-gsm-config"
else
    bashio::log.info "init-gsm-config 'up' script exists"
    # Make sure it's executable
    chmod +x "/etc/s6-overlay/s6-rc.d/init-gsm-config/up"
fi

# Make sure there's a proper "run" script for the longrun service
if [ ! -f "/etc/s6-overlay/s6-rc.d/gsm-sms/run" ]; then
    bashio::log.error "The 'run' script is missing for gsm-sms"
else
    bashio::log.info "gsm-sms 'run' script exists"
    # Make sure it's executable
    chmod +x "/etc/s6-overlay/s6-rc.d/gsm-sms/run"
fi

# Add a down script to the bundle
echo "#!/bin/sh" > "${S6_RC_BUNDLE}/down"
echo "# Bundle down script - nothing to do here" >> "${S6_RC_BUNDLE}/down"
chmod +x "${S6_RC_BUNDLE}/down"

# Make sure gsm-services bundle is removed or renamed to avoid conflicts
if [ -d "/etc/s6-overlay/s6-rc.d/gsm-services" ]; then
    bashio::log.warning "Removing conflicting gsm-services bundle"
    rm -rf "/etc/s6-overlay/s6-rc.d/gsm-services"
fi

# Additional S6-overlay v3 directories required at runtime
mkdir -p /run/s6/legacy-services  # For compatibility
mkdir -p /var/run/s6/services      # For service management

# Remove any existing symlinks first
rm -f /run/s6/services/gsm-sms 2>/dev/null
rm -f /var/run/s6/services/gsm-sms 2>/dev/null

# Create fresh symlinks to the service directories
ln -sf /etc/s6-overlay/s6-rc.d/gsm-sms /run/s6/services/gsm-sms
ln -sf /etc/s6-overlay/s6-rc.d/gsm-sms /var/run/s6/services/gsm-sms

bashio::log.info "S6-RC bundle connection fix complete"
