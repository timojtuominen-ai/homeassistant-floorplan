FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache \
      python3 py3-pip py3-setuptools py3-wheel \
      cmake g++ make musl-dev linux-headers \
  && python3 -m venv /opt/venv \
  && /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
  && /opt/venv/bin/pip install --no-cache-dir pyads==3.6.0 paho-mqtt==2.1.0

COPY run.sh /
COPY app /app
RUN chmod a+x /run.sh
CMD ["/run.sh"]
