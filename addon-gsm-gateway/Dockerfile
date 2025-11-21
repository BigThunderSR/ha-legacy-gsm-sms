ARG BUILD_FROM
FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies required for gammu and python-gammu
RUN apk update \
    && apk add --no-cache \
        python3 \
        python3-dev \
        py3-pip \
        pkgconfig \
        gammu \
        gammu-dev \
        libffi-dev \
        gcc \
        musl-dev \
        linux-headers \
        usb-modeswitch \
        usb-modeswitch-udev \
    && rm -rf /var/cache/apk/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

# Copy application files
COPY run.py .
COPY support.py .
COPY mqtt_publisher.py .
COPY network_codes.py .
COPY run.sh .
COPY icon.png .
COPY services.yaml .

# Make run script executable
RUN chmod +x run.sh

# Expose port
EXPOSE 5000

# Labels
LABEL \
    io.hass.name="GSM SMS Gateway Enhanced" \
    io.hass.description="Enhanced SMS Gammu Gateway with network provider lookup and comprehensive diagnostics" \
    io.hass.type="addon" \
    io.hass.version="2.1.0" \
    maintainer="BigThunderSR"

# Run
CMD [ "./run.sh" ]