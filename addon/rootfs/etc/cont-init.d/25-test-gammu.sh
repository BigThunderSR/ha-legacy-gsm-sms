#!/command/with-contenv bashio
# Run Gammu diagnostic test

bashio::log.info "Running Gammu diagnostic test..."

if [ -f "/usr/bin/test_gammu.py" ]; then
    # Make sure the script is executable
    chmod +x /usr/bin/test_gammu.py
    
    # Run the test script
    python3 /usr/bin/test_gammu.py || true
    
    # Regardless of the test outcome, continue startup
    bashio::log.info "Gammu diagnostic test completed"
else
    bashio::log.warning "Gammu diagnostic test script not found"
fi
