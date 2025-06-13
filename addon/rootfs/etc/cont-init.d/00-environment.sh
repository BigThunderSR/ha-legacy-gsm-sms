#!/usr/bin/with-contenv bashio

# Create required directories
mkdir -p /run/s6/container_environment
mkdir -p /var/run/s6/container_environment

# Copy environment variables
cp -f /etc/cont-env.d/* /run/s6/container_environment/ 2>/dev/null || true
cp -f /etc/cont-env.d/* /var/run/s6/container_environment/ 2>/dev/null || true

# Ensure SUPERVISOR_TOKEN is available
if [ -n "${SUPERVISOR_TOKEN}" ]; then
    echo "${SUPERVISOR_TOKEN}" > /run/s6/container_environment/SUPERVISOR_TOKEN
    echo "${SUPERVISOR_TOKEN}" > /var/run/s6/container_environment/SUPERVISOR_TOKEN
    chmod 600 /run/s6/container_environment/SUPERVISOR_TOKEN
    chmod 600 /var/run/s6/container_environment/SUPERVISOR_TOKEN
else
    bashio::log.warning "No SUPERVISOR_TOKEN environment variable available"
fi

bashio::log.info "Initialization completed"
