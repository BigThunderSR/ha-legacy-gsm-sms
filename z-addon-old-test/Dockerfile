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
COPY queue_sms.sh /usr/bin/

# Create required S6-overlay directories
RUN mkdir -p /etc/services.d \
    && mkdir -p /etc/cont-init.d \
    && mkdir -p /etc/cont-finish.d \
    && mkdir -p /etc/s6-overlay/s6-rc.d/gsm-sms \
    && mkdir -p /etc/s6-overlay/s6-rc.d/init-gsm-config \
    && mkdir -p /etc/s6-overlay/s6-rc.d/gsm-bundle/contents.d \
    && mkdir -p /etc/s6-overlay/s6-rc.d/user/contents.d

# Copy root filesystem
COPY rootfs /

# Set permissions for scripts
RUN chmod a+x /usr/bin/gsm_sms_service.py \
    && chmod a+x /usr/bin/send_sms.sh \
    && chmod a+x /usr/bin/queue_sms.sh \
    && chmod +x /etc/cont-init.d/25-test-gammu.sh \
    && chmod a+x /etc/cont-init.d/*.sh \
    && chmod +x /etc/s6-overlay/s6-rc.d/gsm-sms/run \
    && chmod +x /etc/s6-overlay/s6-rc.d/gsm-sms/finish \
    && chmod +x /etc/s6-overlay/s6-rc.d/init-gsm-config/up \
    && chmod a+x /etc/s6-overlay/s6-rc.d/init-gsm-config/up

# Set permissions for all S6 service scripts
RUN find /etc/s6-overlay/s6-rc.d/ -type f \( -name "run" -o -name "up" -o -name "finish" -o -name "notification-fd" \) -exec chmod +x {} \; \
    && find /etc/cont-init.d/ -type f -exec chmod +x {} \;

# Create essential S6 files if missing
RUN echo "longrun" > /etc/s6-overlay/s6-rc.d/gsm-sms/type \
    && echo "oneshot" > /etc/s6-overlay/s6-rc.d/init-gsm-config/type \
    && echo "bundle" > /etc/s6-overlay/s6-rc.d/gsm-bundle/type \
    && echo "gsm-sms" > /etc/s6-overlay/s6-rc.d/gsm-bundle/contents.d/gsm-sms \
    && echo "init-gsm-config" > /etc/s6-overlay/s6-rc.d/gsm-bundle/contents.d/init-gsm-config \
    && echo "gsm-bundle" > /etc/s6-overlay/s6-rc.d/user/contents.d/gsm-bundle \
    && mkdir -p /etc/s6-overlay/s6-rc.d/gsm-sms/dependencies.d \
    && touch /etc/s6-overlay/s6-rc.d/gsm-sms/dependencies.d/init-gsm-config

# Install required Python packages
RUN pip3 install --no-cache-dir python-gammu==3.2.4 requests

# Labels
LABEL \
    io.hass.name="Legacy GSM SMS" \
    io.hass.description="Use a GSM modem to send and receive SMS messages" \
    io.hass.version="0.0.1a" \
    io.hass.type="addon" \
    io.hass.arch="armhf|aarch64|i386|amd64|armv7"
