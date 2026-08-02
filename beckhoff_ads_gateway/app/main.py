from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from typing import Any

import paho.mqtt.client as mqtt
import pyads

PLC_IP = os.environ["PLC_IP"]
PLC_AMS_NET_ID = os.environ["PLC_AMS_NET_ID"]
LOCAL_AMS_NET_ID = os.environ["LOCAL_AMS_NET_ID"]
PLC_ADS_PORT = int(os.environ["PLC_ADS_PORT"])
POLL_INTERVAL = int(os.environ["POLL_INTERVAL"])
ADS_SYMBOL = os.environ["ADS_SYMBOL"]
ADS_DATA_TYPE = os.environ["ADS_DATA_TYPE"].upper()
ENTITY_NAME = os.environ["ENTITY_NAME"]
ENTITY_ID = os.environ["ENTITY_ID"]
UNIT = os.environ["UNIT_OF_MEASUREMENT"]
DEVICE_CLASS = os.environ["DEVICE_CLASS"]
STATE_CLASS = os.environ["STATE_CLASS"]
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

MQTT_HOST = os.environ["MQTT_HOST"]
MQTT_PORT = int(os.environ["MQTT_PORT"])
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
LOGGER = logging.getLogger("beckhoff_ads_gateway")

ADS_TYPES = {
    "BOOL": pyads.PLCTYPE_BOOL,
    "BYTE": pyads.PLCTYPE_BYTE,
    "WORD": pyads.PLCTYPE_WORD,
    "DWORD": pyads.PLCTYPE_DWORD,
    "INT": pyads.PLCTYPE_INT,
    "UINT": pyads.PLCTYPE_UINT,
    "DINT": pyads.PLCTYPE_DINT,
    "UDINT": pyads.PLCTYPE_UDINT,
    "REAL": pyads.PLCTYPE_REAL,
    "LREAL": pyads.PLCTYPE_LREAL,
}

if ADS_DATA_TYPE not in ADS_TYPES:
    raise RuntimeError(f"Unsupported ADS data type: {ADS_DATA_TYPE}")

DISCOVERY_TOPIC = f"homeassistant/sensor/beckhoff_ads/{ENTITY_ID}/config"
STATE_TOPIC = f"beckhoff_ads/{ENTITY_ID}/state"
AVAILABILITY_TOPIC = "beckhoff_ads/status"

stop_requested = False


def stop_handler(_signum: int, _frame: Any) -> None:
    global stop_requested
    stop_requested = True


signal.signal(signal.SIGTERM, stop_handler)
signal.signal(signal.SIGINT, stop_handler)


def create_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="beckhoff_ads_gateway",
    )
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.will_set(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    discovery = {
        "name": ENTITY_NAME,
        "unique_id": f"beckhoff_ads_{ENTITY_ID}",
        "object_id": ENTITY_ID,
        "state_topic": STATE_TOPIC,
        "availability_topic": AVAILABILITY_TOPIC,
        "payload_available": "online",
        "payload_not_available": "offline",
        "unit_of_measurement": UNIT,
        "device_class": DEVICE_CLASS,
        "state_class": STATE_CLASS,
        "device": {
            "identifiers": ["beckhoff_cx5000_ads"],
            "name": "Beckhoff CX5000",
            "manufacturer": "Beckhoff",
            "model": "TwinCAT 2",
        },
        "origin": {
            "name": "Beckhoff ADS Gateway",
            "sw_version": "0.3.0",
            "support_url": "https://github.com/timojtuominen-ai/homeassistant-floorplan",
        },
    }

    client.publish(DISCOVERY_TOPIC, json.dumps(discovery), qos=1, retain=True)
    client.publish(AVAILABILITY_TOPIC, "online", qos=1, retain=True)
    return client


def configure_local_ads() -> None:
    pyads.open_port()
    try:
        pyads.set_local_address(LOCAL_AMS_NET_ID)
    finally:
        pyads.close_port()

    LOGGER.info("Local AMS Net ID set to %s", LOCAL_AMS_NET_ID)


def connect_plc() -> pyads.Connection:
    configure_local_ads()
    plc = pyads.Connection(PLC_AMS_NET_ID, PLC_ADS_PORT, PLC_IP)
    plc.open()
    LOGGER.info("ADS connection opened to %s", PLC_IP)
    LOGGER.info("PLC state: %s", plc.read_state())
    return plc


def main() -> int:
    client = create_mqtt_client()
    plc: pyads.Connection | None = None

    try:
        while not stop_requested:
            try:
                if plc is None or not plc.is_open:
                    plc = connect_plc()

                value = plc.read_by_name(ADS_SYMBOL, ADS_TYPES[ADS_DATA_TYPE])
                LOGGER.info("%s = %s", ADS_SYMBOL, value)
                client.publish(STATE_TOPIC, str(value), qos=1, retain=True)
                client.publish(AVAILABILITY_TOPIC, "online", qos=1, retain=True)

            except Exception:
                LOGGER.exception("ADS read failed")
                client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)

                if plc is not None:
                    try:
                        plc.close()
                    except Exception:
                        pass
                    plc = None

            for _ in range(POLL_INTERVAL * 10):
                if stop_requested:
                    break
                time.sleep(0.1)

        return 0

    finally:
        if plc is not None:
            try:
                plc.close()
            except Exception:
                pass

        client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    sys.exit(main())
