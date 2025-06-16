#!/command/with-contenv bashio

# Get log level from config
LOG_LEVEL=$(bashio::config 'log_level')
bashio::log.level "${LOG_LEVEL}"

# Environment setup is now handled automatically by the s6-overlay
bashio::log.info "Setting up environment..."

# Ensure PYTHONUNBUFFERED is set for better logging
export PYTHONUNBUFFERED=1

bashio::log.info "Environment setup completed"
