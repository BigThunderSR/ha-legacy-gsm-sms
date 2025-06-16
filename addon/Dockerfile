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
    python3-dev \
    jq \
    curl \
    bash

# Copy the service files
COPY gsm_sms_service.py /usr/bin/
COPY send_sms.sh /usr/bin/

# Install Python dependencies
RUN pip3 install --no-cache-dir requests gammu

# Copy root filesystem
COPY rootfs /

# Set permissions for scripts
RUN chmod a+x /usr/bin/gsm_sms_service.py \
    && chmod a+x /usr/bin/send_sms.sh \
    && chmod a+x /etc/services.d/gsm_sms/run \
    && chmod a+x /etc/services.d/gsm_sms/finish \
    && chmod a+x /etc/cont-init.d/*.sh \
    && chmod a+x /etc/s6-overlay/s6-rc.d/init-gsm-config/up \
    && chmod a+x /etc/s6-overlay/s6-rc.d/gsm-sms/run \
    && chmod a+x /etc/s6-overlay/s6-rc.d/gsm-sms/finish

# Install required Python packages
RUN pip3 install --no-cache-dir python-gammu==3.2.4 requests

# Debug logging
ENV S6_VERBOSITY=3
ENV S6_CMD_WAIT_FOR_SERVICES=1
ENV S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0

# Labels
LABEL \
    io.hass.name="Legacy GSM SMS" \
    io.hass.description="Use a GSM modem to send and receive SMS messages" \
    io.hass.version="0.0.1d" \
    io.hass.type="addon" \
    io.hass.arch="armhf|aarch64|i386|amd64|armv7"
