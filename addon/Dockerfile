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

# Copy the integration files
WORKDIR /app
COPY custom_components/legacy_gsm_sms/*.py /app/
COPY run.sh /
RUN chmod a+x /run.sh

# Install required Python packages
RUN pip3 install --no-cache-dir python-gammu==3.2.4

# Labels
LABEL \
    io.hass.name="Legacy GSM SMS" \
    io.hass.description="Use a GSM modem to send and receive SMS messages" \
    io.hass.version="1.0.0" \
    io.hass.type="addon" \
    io.hass.arch="armhf|aarch64|i386|amd64|armv7"

ENTRYPOINT ["/run.sh"]
