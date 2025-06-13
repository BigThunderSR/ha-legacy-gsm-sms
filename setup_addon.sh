#!/bin/bash

echo "Setting up Legacy GSM SMS as a Home Assistant Addon..."

# Create directories if they don't exist
mkdir -p ~/.homeassistant/addons/legacy_gsm_sms

# Copy addon files
cp -r addon/* ~/.homeassistant/addons/legacy_gsm_sms/
cp repository.yaml ~/.homeassistant/addons/

echo "Setup complete!"
echo "Please restart Home Assistant and look for 'Legacy GSM SMS' in your Add-on Store."
