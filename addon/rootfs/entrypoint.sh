#!/usr/bin/env bash

# Enable job control
set -m

# This script is executed directly when the container is run, and is responsible
# for starting the s6-overlay

# Create required directories
mkdir -p /run/s6/container_environment
mkdir -p /var/run/s6/container_environment

# If SUPERVISOR_TOKEN is set, save it to files that S6 can use
if [ -n "$SUPERVISOR_TOKEN" ]; then
    echo "$SUPERVISOR_TOKEN" > /run/s6/container_environment/SUPERVISOR_TOKEN
    echo "$SUPERVISOR_TOKEN" > /var/run/s6/container_environment/SUPERVISOR_TOKEN
    chmod 600 /run/s6/container_environment/SUPERVISOR_TOKEN
    chmod 600 /var/run/s6/container_environment/SUPERVISOR_TOKEN
fi

# Start s6-overlay
exec /init
