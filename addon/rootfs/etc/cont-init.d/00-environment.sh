#!/command/with-contenv bashio

# Environment setup is now handled automatically by the s6-overlay
bashio::log.info "Setting up environment..."

# Ensure PYTHONUNBUFFERED is set for better logging
export PYTHONUNBUFFERED=1

bashio::log.info "Environment setup completed"
