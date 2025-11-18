ARG BUILD_FROM
FROM $BUILD_FROM

# Install runtime dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    jq

# Install Python packages
RUN pip3 install --no-cache-dir --break-system-packages \
    pyserial \
    requests

# Copy scripts
COPY run.sh /
COPY rootfs /

# Make scripts executable
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
