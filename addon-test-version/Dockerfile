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
    python3-dev \
    jq

# Install Python packages
RUN pip3 install --break-system-packages --no-cache-dir \
    python-gammu==3.2.4 \
    requests

# Copy files
COPY run.sh /
COPY rootfs /

# Set permissions
RUN chmod a+x /run.sh \
    && chmod a+x /usr/bin/gsm_sms_service.py

CMD [ "/run.sh" ]

# Labels
LABEL \
    io.hass.name="Legacy GSM SMS Test" \
    io.hass.description="GSM SMS addon test version" \
    io.hass.version="0.1.0" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64"
