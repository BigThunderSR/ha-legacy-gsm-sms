#!/usr/bin/with-contenv bashio

# Fix permissions on important directories
chmod 755 /app
chmod 755 /data/gsm_sms 2>/dev/null || true

# Make service scripts executable
chmod a+x /app/gsm_sms_service.py
chmod a+x /app/send_sms.sh

bashio::log.info "Permissions fixed"
