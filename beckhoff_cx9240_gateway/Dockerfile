ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.21
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip build-base linux-headers curl
RUN pip3 install --no-cache-dir --break-system-packages pyads==3.4.0 paho-mqtt==2.1.0

# Pin the tested TC3 gateway implementation used during CX9240 bench testing.
RUN curl -fsSL https://raw.githubusercontent.com/timojtuominen-ai/homeassistant-floorplan/7b29bcf5790e7d484c5572c21bf97208b360d4d0/beckhoff_tc3_gateway/main.py -o /app/main.py \
 && curl -fsSL https://raw.githubusercontent.com/timojtuominen-ai/homeassistant-floorplan/7b29bcf5790e7d484c5572c21bf97208b360d4d0/beckhoff_tc3_gateway/entities.json -o /app/entities.json

# Production mode is hard-locked OFF from TEST mode so existing floorplan / legacy entity IDs are reused.
RUN sed -i 's/TEST = bool(OPT.get("test_mode", True))/TEST = False/' /app/main.py \
 && sed -i 's/Kotiautomaatio_TC3 v0.22/Kotiautomaatio_TC3 v0.29.6/' /app/main.py \
 && sed -i 's/Starting Beckhoff TC3 Gateway TEST v0.1.5/Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.0/' /app/main.py

# Remove the rarely useful acknowledgement diagnostic from Home Assistant.
RUN python3 - <<'PY'
import json
p='/app/entities.json'
d=json.load(open(p, encoding='utf-8'))
d['binary_sensors']=[e for e in d.get('binary_sensors',[]) if e.get('symbol') != 'GVL_HA.xFireAckActive']
with open(p,'w',encoding='utf-8') as f:
    json.dump(d,f,ensure_ascii=False,indent=2)
PY

COPY run.sh /run.sh
RUN chmod a+x /run.sh
CMD ["/run.sh"]
