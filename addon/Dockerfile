ARG BUILD_FROM
FROM $BUILD_FROM

# Add required packages
RUN apk add --no-cache \
    python3 \
    py3-pip \
    gammu \
    bluez \
    bluez-libs \
    gcc \
    musl-dev \
    python3-dev

# Copy the service files
WORKDIR /app
COPY gsm_sms_service.py /app/
COPY send_sms.sh /app/
COPY run.sh /
RUN chmod a+x /run.sh
RUN chmod a+x /app/gsm_sms_service.py
RUN chmod a+x /app/send_sms.sh

# Install required Python packages and tools
RUN apk add --no-cache jq curl
RUN pip3 install --no-cache-dir python-gammu==3.2.4 requests

# Labels
LABEL \
    io.hass.name="Legacy GSM SMS" \
    io.hass.description="Use a GSM modem to send and receive SMS messages" \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="armhf|aarch64|i386|amd64|armv7"

ENTRYPOINT ["/run.sh"]
