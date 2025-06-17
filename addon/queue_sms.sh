#!/usr/bin/with-contenv bashio
# ==============================================================================
# Script to add SMS to the pending queue
# ==============================================================================

# Get command line arguments
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <phone_number> <message>"
  exit 1
fi

PHONE_NUMBER=$1
MESSAGE=$2

# Create the pending SMS directory
mkdir -p /data/gsm_sms/pending

# Create a unique filename
TIMESTAMP=$(date +%s)
RANDOM_ID=$RANDOM
FILENAME="${TIMESTAMP}-${RANDOM_ID}.sms"
FILE_PATH="/data/gsm_sms/pending/${FILENAME}"

# Create the SMS file
cat > "$FILE_PATH" << EOL
{
  "target": "${PHONE_NUMBER}",
  "message": "${MESSAGE}"
}
EOL

# Verify the file was created
if [ -f "$FILE_PATH" ]; then
  echo "SMS queued successfully: ${FILENAME}"
  exit 0
else
  echo "Failed to queue SMS"
  exit 1
fi
