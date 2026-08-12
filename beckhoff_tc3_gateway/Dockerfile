ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.21
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip build-base linux-headers
RUN pip3 install --no-cache-dir --break-system-packages pyads==3.4.0 paho-mqtt==2.1.0

COPY run.sh /run.sh
COPY main.py /app/main.py
COPY entities.json /app/entities.json
RUN chmod a+x /run.sh
CMD ["/run.sh"]
