ARG BUILD_FROM

# Alpine's gammu (1.42.0) is too old for python-gammu >= 3.4, so build both from source
FROM $BUILD_FROM AS gammu-wheel
# renovate: datasource=github-release-attachments depName=gammu/gammu
ARG GAMMU_VERSION=1.45.1
ARG GAMMU_SHA256=09c32e0573db6c26b23c185ce0e5600677bd57bf98cf7ec69557e24a5cad7c40
# renovate: datasource=github-release-attachments depName=gammu/python-gammu
ARG PYTHON_GAMMU_VERSION=3.5.0
ARG PYTHON_GAMMU_SHA256=5d8a3e38a0a0fb13103dedb24a5d695f6fb3b3dd6ff16d3bb55bf4dec71bdcfe
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apk add --no-cache \
        python3 python3-dev py3-pip cmake make gcc g++ musl-dev pkgconf \
        curl curl-dev libusb-dev gettext-dev glib-dev patchelf
WORKDIR /build
RUN curl -fsSLo gammu.tar.gz "https://github.com/gammu/gammu/releases/download/${GAMMU_VERSION}/Gammu-${GAMMU_VERSION}.tar.gz" \
    && echo "${GAMMU_SHA256}  gammu.tar.gz" | sha256sum -c - \
    && tar xzf gammu.tar.gz \
    && cmake -S "Gammu-${GAMMU_VERSION}" -B gammu-build -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release \
        -DWITH_BLUETOOTH=OFF -DBUILD_TESTING=OFF -DBUILD_GAMMU=OFF -DBUILD_DOC=OFF \
    && cmake --build gammu-build -j"$(nproc)" --target libGammu gsmsd \
    && (cmake --install gammu-build || true) \
    && test "$(pkg-config --modversion gammu)" = "${GAMMU_VERSION}"
RUN python3 -m venv /venv \
    && /venv/bin/pip install --no-cache-dir auditwheel \
    && echo "python-gammu==${PYTHON_GAMMU_VERSION} --hash=sha256:${PYTHON_GAMMU_SHA256}" > /build/req.txt \
    && /venv/bin/pip wheel --no-cache-dir --no-deps --no-binary python-gammu --require-hashes -w /build/raw -r /build/req.txt \
    && /venv/bin/auditwheel repair /build/raw/*.whl --plat "musllinux_1_2_$(uname -m)" -w /wheelhouse

FROM $BUILD_FROM

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install system dependencies
RUN apk update \
    && apk add --no-cache \
        python3 \
        python3-dev \
        py3-pip \
        pkgconfig \
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
COPY --from=gammu-wheel /wheelhouse /tmp/wheelhouse
RUN pip3 install --break-system-packages --no-cache-dir /tmp/wheelhouse/*.whl \
    && rm -rf /tmp/wheelhouse
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
COPY config.yaml .

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