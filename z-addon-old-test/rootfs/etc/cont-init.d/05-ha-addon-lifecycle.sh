#!/command/with-contenv bashio
# ==============================================================================
# Handle Home Assistant Add-on internal lifecycle for S6-Overlay v3
# ==============================================================================

# Mimic old S6 lifecycle events for Home Assistant
mkdir -p /etc/services.d/s6-fakeservice

# Create notifications directory
mkdir -p /var/run/s6/etc/

bashio::log.info "Creating Home Assistant Add-on lifecycle hooks"

# This will signal to Home Assistant that services are running
cat > /etc/services.d/s6-fakeservice/run << 'EOF'
#!/bin/sh

# Notify Home Assistant that all service are up and running
if [ -d /var/run/s6/etc ]; then
  # Notify Home Assistant we're ready
  touch /var/run/s6/etc/services-up
fi

# Keep the service running
while true; do
  sleep 86400
done

EOF
chmod +x /etc/services.d/s6-fakeservice/run

# This will signal to Home Assistant when the add-on is shutting down
cat > /etc/services.d/s6-fakeservice/finish << 'EOF'
#!/bin/sh

# Signal to Home Assistant the container is shutting down
if [ -d /var/run/s6 ]; then
  # Remove the services-up flag
  rm -f /var/run/s6/etc/services-up
fi

exit 0
EOF
chmod +x /etc/services.d/s6-fakeservice/finish

bashio::log.info "Home Assistant Add-on lifecycle hooks created"
