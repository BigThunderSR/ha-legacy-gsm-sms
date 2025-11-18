ARG BUILD_FROM
FROM $BUILD_FROM

# Install required packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gammu \
    gammu-dev \
    gcc \
    musl-dev \
    python3-dev

# Install Python packages
RUN pip3 install --break-system-packages --no-cache-dir \
    python-gammu==3.2.4 \
    requests

# Copy service files
COPY rootfs /

# Set permissions
RUN chmod a+x /etc/services.d/gsm_sms/run \
    && chmod a+x /etc/services.d/gsm_sms/finish \
    && chmod a+x /usr/bin/gsm_sms_service.py

# Labels
LABEL \
    io.hass.name="Legacy GSM SMS Test" \
    io.hass.description="GSM SMS addon test version" \
    io.hass.version="0.1.0" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"
