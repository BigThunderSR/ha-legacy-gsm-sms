#!/usr/bin/env bashio
set -e

CONFIG_PATH=/data/options.json
# Get version from addon info - try multiple possible locations
VERSION=""
if [ -f "/data/addon_config.json" ]; then
    VERSION=$(jq --raw-output '.version // empty' /data/addon_config.json 2>/dev/null || echo "")
fi
if [ -z "$VERSION" ] && [ -f "/data/addon_info.json" ]; then
    VERSION=$(jq --raw-output '.version // empty' /data/addon_info.json 2>/dev/null || echo "")
fi
if [ -z "$VERSION" ] && [ -f "${CONFIG_PATH}" ]; then
    VERSION=$(jq --raw-output '.version // empty' ${CONFIG_PATH} 2>/dev/null || echo "")
fi
if [ -z "$VERSION" ]; then
    # Last resort - read from config.yaml in the addon directory
    VERSION=$(grep "^version:" /config.yaml 2>/dev/null | awk '{print $2}' || echo "unknown")
fi
# Ensure VERSION is never empty
VERSION=${VERSION:-unknown}

echo "[INFO] =========================================="
echo "[INFO] Legacy GSM SMS (Test) - Version ${VERSION}"
echo "[INFO] =========================================="
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
    
    # If it's a symlink, check the actual device too
    if [ -L "${DEVICE}" ]; then
        REAL_DEVICE=$(readlink -f "${DEVICE}")
        echo "[INFO] Real device: ${REAL_DEVICE}"
        ls -la "${REAL_DEVICE}" 2>/dev/null || echo "[WARNING] Could not stat real device"
        
        # Check if real device is in use
        echo "[INFO] Checking if device is in use..."
        lsof "${REAL_DEVICE}" 2>/dev/null || echo "[INFO] No processes found using device (or lsof failed)"
        fuser "${REAL_DEVICE}" 2>/dev/null && echo "[WARNING] Device is in use!" || echo "[INFO] Device appears free"
        
        # Fix permissions on the real device
        echo "[INFO] Setting device permissions..."
        chmod 666 "${REAL_DEVICE}" 2>/dev/null && echo "[INFO] Permissions set successfully" || echo "[WARNING] Could not set permissions"
        ls -la "${REAL_DEVICE}"
        
        # Try using the real device path instead of symlink
        echo "[INFO] Will try using real device path: ${REAL_DEVICE}"
        DEVICE="${REAL_DEVICE}"
    fi
else
    echo "[WARNING] Device does not exist: ${DEVICE}"
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
