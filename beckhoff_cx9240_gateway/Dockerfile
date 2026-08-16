ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.21
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip build-base linux-headers curl
RUN pip3 install --no-cache-dir --break-system-packages pyads==3.4.0 paho-mqtt==2.1.0
RUN mkdir -p /app

# Production-specific gateway keeps the original Home Assistant MQTT Discovery
# identities so the existing floorplan entities continue working unchanged.
COPY main.py /app/main.py
RUN curl -fsSL https://raw.githubusercontent.com/timojtuominen-ai/homeassistant-floorplan/f28f0cf8990efbc5a231ebed8476b0713a946219/beckhoff_tc3_gateway/entities.json -o /app/entities.json

# v1.0.3 adds commissioning statuses plus writable heating setpoints/temperature offsets.
COPY patch_v103.py /tmp/patch_v103.py
RUN python3 /tmp/patch_v103.py && rm /tmp/patch_v103.py

# v1.0.6 adds Service diagnostics, floor-heating temperatures and fault inputs.
COPY patch_v106.py /tmp/patch_v106.py
RUN python3 /tmp/patch_v106.py && rm /tmp/patch_v106.py

# v1.0.7 reads the floor-heating pressure alarm directly from GVL_Alarm.
COPY patch_v107.py /tmp/patch_v107.py
RUN python3 /tmp/patch_v107.py && rm /tmp/patch_v107.py

# v1.0.8 publishes hot-tub temperatures and circulation-pump control.
COPY patch_v108.py /tmp/patch_v108.py
RUN python3 /tmp/patch_v108.py && rm /tmp/patch_v108.py

# v1.0.9 publishes the actual final state of the main yard lights.
COPY patch_v109.py /tmp/patch_v109.py
RUN python3 /tmp/patch_v109.py && rm /tmp/patch_v109.py

# v1.0.10 publishes four independent moisture-detector states from PLC v0.33.0.
COPY patch_v110.py /tmp/patch_v110.py
RUN python3 /tmp/patch_v110.py && rm /tmp/patch_v110.py

# v1.0.11 connects the HA fire-bell inhibit switch to the PLC 20 minute timer.
COPY patch_v111.py /tmp/patch_v111.py
RUN python3 /tmp/patch_v111.py && rm /tmp/patch_v111.py

# v1.0.12 publishes the sauna PT1000 rate-of-rise heat detector from PLC v0.34.0.
COPY patch_v112.py /tmp/patch_v112.py
RUN python3 /tmp/patch_v112.py && rm /tmp/patch_v112.py

# v1.0.13 publishes the five outbuilding lights and garage temperature.
COPY patch_v113.py /tmp/patch_v113.py
RUN python3 /tmp/patch_v113.py && rm /tmp/patch_v113.py

# v1.0.14 publishes group-off buttons and cleaning-light mode switches.
COPY patch_v114.py /tmp/patch_v114.py
RUN python3 /tmp/patch_v114.py && rm /tmp/patch_v114.py

# v1.0.15 removes retained MQTT Discovery configs from the obsolete gateway device.
COPY patch_v115.py /tmp/patch_v115.py
RUN python3 /tmp/patch_v115.py && rm /tmp/patch_v115.py

# v1.0.16 publishes PLC v0.35.0 persistent light, pushbutton and door counters.
COPY patch_v116.py /tmp/patch_v116.py
RUN python3 /tmp/patch_v116.py && rm /tmp/patch_v116.py

# v1.0.17 publishes actual PLC room-heating demand states.
COPY patch_v117.py /tmp/patch_v117.py
RUN python3 /tmp/patch_v117.py && rm /tmp/patch_v117.py

# v1.0.18 publishes actual downstairs room-heating demand states.
COPY patch_v118.py /tmp/patch_v118.py
RUN python3 /tmp/patch_v118.py && rm /tmp/patch_v118.py

COPY run.sh /run.sh
RUN chmod a+x /run.sh
CMD ["/run.sh"]
