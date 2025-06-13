#!/command/with-contenv bashio

# Create data directory if needed
mkdir -p /data/gsm_sms 2>/dev/null || true

# Fix permissions on important directories
chmod 755 /data/gsm_sms 2>/dev/null || true

# Make service scripts executable (although this should be done in Dockerfile)
chmod a+x /usr/bin/gsm_sms_service.py
chmod a+x /usr/bin/send_sms.sh

bashio::log.info "Permissions fixed"
