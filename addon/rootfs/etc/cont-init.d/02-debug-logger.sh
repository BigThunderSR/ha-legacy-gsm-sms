#!/bin/bash

# This script will help diagnose issues with the addon
# It will run continuously in the background logging system info

LOG_FILE="/share/gsm_sms_debug.log"

# Create a clean log file
echo "=== GSM SMS Debug Log Started at $(date) ===" > $LOG_FILE

# Function to log system information
log_system_info() {
    echo "=== System Info Snapshot at $(date) ===" >> $LOG_FILE
    echo "Processes:" >> $LOG_FILE
    ps aux >> $LOG_FILE
    echo "" >> $LOG_FILE
    
    echo "S6 Service Status:" >> $LOG_FILE
    if [ -d "/run/s6/services" ]; then
        ls -la /run/s6/services >> $LOG_FILE
    else 
        echo "s6 services directory not found" >> $LOG_FILE
    fi
    echo "" >> $LOG_FILE
    
    echo "System Log (tail):" >> $LOG_FILE
    tail -n 20 /var/log/messages 2>/dev/null >> $LOG_FILE || echo "Cannot access system log" >> $LOG_FILE
    echo "" >> $LOG_FILE
    
    # Check if modem device exists
    MODEM_DEVICE=$(jq -r '.device' /data/gsm_sms/config.json 2>/dev/null || echo "/dev/ttyUSB0")
    echo "Modem device ($MODEM_DEVICE) status:" >> $LOG_FILE
    if [ -e "$MODEM_DEVICE" ]; then
        ls -la $MODEM_DEVICE >> $LOG_FILE
    else
        echo "Modem device not found" >> $LOG_FILE
    fi
    echo "" >> $LOG_FILE

    # Check running services
    echo "Our GSM SMS Service process status:" >> $LOG_FILE
    pgrep -f "gsm_sms_service.py" >> $LOG_FILE || echo "GSM SMS service not running" >> $LOG_FILE
    echo "" >> $LOG_FILE
}

# Log initial system info
log_system_info

# Continuous monitoring in the background
while true; do
    log_system_info
    sleep 60  # Log every minute
done &

# Let the script continue running in the background
