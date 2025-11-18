ARG BUILD_FROM
FROM $BUILD_FROM

# Install runtime dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    bashio \
    jq

# Install Python packages
RUN pip3 install --no-cache-dir --break-system-packages \
    pyserial \
    requests

# Copy service script
COPY rootfs /

# Make scripts executable
RUN chmod a+x /etc/services.d/gsm-sms/run \
    && chmod a+x /etc/services.d/gsm-sms/finish

CMD []
