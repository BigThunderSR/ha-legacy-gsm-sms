#!/usr/bin/env bashio
set -e

CONFIG_PATH=/data/options.json

echo "[INFO] Starting GSM SMS Service..."

# Get configuration from JSON file directly
DEVICE=$(jq --raw-output '.device // "/dev/ttyUSB0"' $CONFIG_PATH)
BAUD_SPEED=$(jq --raw-output '.baud_speed // "0"' $CONFIG_PATH)
SCAN_INTERVAL=$(jq --raw-output '.scan_interval // "30"' $CONFIG_PATH)
LOG_LEVEL=$(jq --raw-output '.log_level // "info"' $CONFIG_PATH)

echo "[INFO] Device: ${DEVICE}"
echo "[INFO] Baud Speed: ${BAUD_SPEED}"
echo "[INFO] Scan Interval: ${SCAN_INTERVAL}"
echo "[INFO] Log Level: ${LOG_LEVEL}"

# Check if device exists and permissions
if [ -e "${DEVICE}" ]; then
    echo "[INFO] Device exists: ${DEVICE}"
    ls -la "${DEVICE}"
else
    echo "[WARNING] Device does not exist: ${DEVICE}"
fi

# Check if device is in use
if lsof 2>/dev/null | grep -q "${DEVICE}"; then
    echo "[WARNING] Device may be in use by another process"
    lsof 2>/dev/null | grep "${DEVICE}" || true
fi

# Export configuration as environment variables
export DEVICE
export BAUD_SPEED
export SCAN_INTERVAL
export LOG_LEVEL
export PYTHONUNBUFFERED=1

# Start the Python service
echo "[INFO] Executing Python service..."
exec python3 /usr/bin/gsm_sms_service.py
