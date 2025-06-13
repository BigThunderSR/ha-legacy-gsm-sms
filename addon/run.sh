#!/usr/bin/with-contenv bashio

# This is a helper script that is no longer called directly by the addon
# The functionality has been moved to rootfs/etc/services.d/gsm_sms/run

bashio::log.info "Legacy GSM SMS helper script"
bashio::log.info "This script is now replaced by S6 overlay services"

# Stay alive - this should never be called directly
sleep infinity
