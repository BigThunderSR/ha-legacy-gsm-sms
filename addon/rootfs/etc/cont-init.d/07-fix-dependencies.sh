#!/command/with-contenv bashio

# Get log level from config
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

bashio::log.info "Fixing service dependencies..."

# Clean up and recreate the dependencies directory
rm -rf /etc/s6-overlay/s6-rc.d/gsm-sms/dependencies.d
mkdir -p /etc/s6-overlay/s6-rc.d/gsm-sms/dependencies.d

# Add the init-gsm-config dependency
echo "" > /etc/s6-overlay/s6-rc.d/gsm-sms/dependencies.d/init-gsm-config

# Check for the finish script
if [ ! -f "/etc/s6-overlay/s6-rc.d/gsm-sms/finish" ]; then
    bashio::log.info "Creating missing finish script for gsm-sms"
    cat > /etc/s6-overlay/s6-rc.d/gsm-sms/finish << 'EOF'
#!/bin/sh
# Finish script for GSM SMS service

# Try to gracefully stop the Python process if possible
if [ -n "$1" ]; then
  # Send TERM signal to the entire process group
  /bin/kill -TERM -- -$1 2>/dev/null
fi

# The exit code is 0 to avoid restarting the service
exit 0
EOF
    chmod 755 /etc/s6-overlay/s6-rc.d/gsm-sms/finish
fi

# Create an S6 notification-fd script to properly manage service startup notification
mkdir -p /etc/s6-overlay/s6-rc.d/gsm-sms/data
cat > /etc/s6-overlay/s6-rc.d/gsm-sms/notification-fd << 'EOF'
#!/bin/sh
# Notification FD for S6 services
if [ -d /var/run/s6/container_environment ]; then
  # S6 Overlay v3 behavior
  echo "3"
else 
  echo "1"
fi
EOF
chmod 755 /etc/s6-overlay/s6-rc.d/gsm-sms/notification-fd

bashio::log.info "Service dependencies fixed"
