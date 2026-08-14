ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.21
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip build-base linux-headers curl
RUN pip3 install --no-cache-dir --break-system-packages pyads==3.4.0 paho-mqtt==2.1.0
RUN mkdir -p /app

# Production-specific gateway keeps the original Home Assistant MQTT Discovery
# identities so the existing floorplan entities continue working unchanged.
COPY main.py /app/main.py
RUN curl -fsSL https://raw.githubusercontent.com/timojtuominen-ai/homeassistant-floorplan/77efde2e6cc0a088cb69c37d44bf7759b5f3ba8a/beckhoff_tc3_gateway/entities.json -o /app/entities.json

# v1.0.3 adds commissioning statuses plus writable heating setpoints/temperature offsets.
COPY patch_v103.py /tmp/patch_v103.py
RUN python3 /tmp/patch_v103.py && rm /tmp/patch_v103.py

COPY run.sh /run.sh
RUN chmod a+x /run.sh
CMD ["/run.sh"]
