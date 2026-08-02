from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
from typing import Any, Callable

import paho.mqtt.client as mqtt
import pyads

PLC_IP = os.environ["PLC_IP"]
PLC_AMS_NET_ID = os.environ["PLC_AMS_NET_ID"]
LOCAL_AMS_NET_ID = os.environ["LOCAL_AMS_NET_ID"]
PLC_ADS_PORT = int(os.environ["PLC_ADS_PORT"])
POLL_INTERVAL = int(os.environ["POLL_INTERVAL"])

INDEX_GROUP_TEXT = os.environ["INDEX_GROUP"]
INDEX_OFFSET_TEXT = os.environ["INDEX_OFFSET"]
INDEX_GROUP = int(INDEX_GROUP_TEXT, 0)
INDEX_OFFSET = int(INDEX_OFFSET_TEXT, 0)
ADS_DATA_TYPE = os.environ["ADS_DATA_TYPE"].upper()
VALUE_SCALE = float(os.environ["VALUE_SCALE"])
VALUE_OFFSET = float(os.environ["VALUE_OFFSET"])
VALUE_PRECISION = int(os.environ["VALUE_PRECISION"])

ENTITY_NAME = os.environ["ENTITY_NAME"]
ENTITY_ID = os.environ["ENTITY_ID"]
UNIT = os.environ["UNIT_OF_MEASUREMENT"]
DEVICE_CLASS = os.environ["DEVICE_CLASS"]
STATE_CLASS = os.environ["STATE_CLASS"]
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG").upper()
ADD_LOCAL_ROUTE = os.environ.get("ADD_LOCAL_ROUTE", "true").lower() == "true"

MQTT_HOST = os.environ["MQTT_HOST"]
MQTT_PORT = int(os.environ["MQTT_PORT"])
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
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
RAW_TOPIC = f"beckhoff_ads/{ENTITY_ID}/raw"
AVAILABILITY_TOPIC = "beckhoff_ads/status"

stop_requested = False


def stop_handler(_signum: int, _frame: Any) -> None:
    global stop_requested
    stop_requested = True


signal.signal(signal.SIGTERM, stop_handler)
signal.signal(signal.SIGINT, stop_handler)


def log_step(number: int, title: str) -> None:
    LOGGER.info("[%s/7] %s", number, title)


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
        "suggested_display_precision": VALUE_PRECISION,
        "json_attributes_topic": RAW_TOPIC,
        "device": {
            "identifiers": ["beckhoff_cx5000_ads"],
            "name": "Beckhoff CX5000",
            "manufacturer": "Beckhoff",
            "model": "TwinCAT 2 TcBA",
        },
        "origin": {
            "name": "Beckhoff ADS Gateway",
            "sw_version": "0.3.5",
            "support_url": "https://github.com/timojtuominen-ai/homeassistant-floorplan",
        },
    }

    client.publish(DISCOVERY_TOPIC, json.dumps(discovery), qos=1, retain=True)
    client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
    LOGGER.info("MQTT discovery published")
    return client


def configure_local_ads() -> None:
    log_step(1, "Opening local ADS router")
    port = pyads.open_port()
    try:
        LOGGER.info("Local ADS router port opened: %s", port)

        log_step(2, f"Setting local AMS Net ID to {LOCAL_AMS_NET_ID}")
        pyads.set_local_address(LOCAL_AMS_NET_ID)
        LOGGER.info("Actual local ADS address: %s", pyads.get_local_address())

        if ADD_LOCAL_ROUTE:
            log_step(3, f"Adding explicit local route {PLC_AMS_NET_ID} -> {PLC_IP}")
            pyads.add_route(PLC_AMS_NET_ID, PLC_IP)
            LOGGER.info("Explicit local ADS route added")
        else:
            log_step(3, "Skipping explicit local ADS route")
    finally:
        pyads.close_port()
        LOGGER.info("Local ADS router setup port closed")


def connect_plc() -> pyads.Connection:
    log_step(
        4,
        f"Opening ADS connection to {PLC_AMS_NET_ID}:{PLC_ADS_PORT} at {PLC_IP}",
    )
    connection = pyads.Connection(PLC_AMS_NET_ID, PLC_ADS_PORT, PLC_IP)
    connection.open()
    LOGGER.info("ADS connection object opened")
    LOGGER.info("Connection local address: %s", connection.get_local_address())
    return connection


def run_probe(
    number: int,
    title: str,
    probe: Callable[[], Any],
) -> tuple[bool, Any | None]:
    log_step(number, title)
    try:
        result = probe()
        LOGGER.info("%s succeeded: %r", title, result)
        return True, result
    except Exception as err:
        LOGGER.exception("%s failed (%s: %s)", title, type(err).__name__, err)
        return False, None


def read_process_value(connection: pyads.Connection) -> tuple[Any, float]:
    log_step(
        7,
        (
            f"Reading direct ADS memory IG={INDEX_GROUP_TEXT}, "
            f"IO={INDEX_OFFSET_TEXT}, type={ADS_DATA_TYPE}"
        ),
    )
    raw = connection.read(
        INDEX_GROUP,
        INDEX_OFFSET,
        ADS_TYPES[ADS_DATA_TYPE],
    )
    scaled = round((float(raw) * VALUE_SCALE) + VALUE_OFFSET, VALUE_PRECISION)
    LOGGER.info("Direct ADS read succeeded: raw=%r, scaled=%s %s", raw, scaled, UNIT)
    return raw, scaled


def main() -> int:
    client = create_mqtt_client()
    plc: pyads.Connection | None = None
    state_ok = False
    info_ok = False
    state = None
    device_info = None

    try:
        configure_local_ads()
        plc = connect_plc()

        state_ok, state = run_probe(5, "Reading ADS state", plc.read_state)
        info_ok, device_info = run_probe(
            6,
            "Reading ADS device info",
            plc.read_device_info,
        )

        LOGGER.info(
            "=== ADS DIAGNOSTIC SUMMARY: state_ok=%s device_info_ok=%s ===",
            state_ok,
            info_ok,
        )

        while not stop_requested:
            try:
                if plc is None or not plc.is_open:
                    configure_local_ads()
                    plc = connect_plc()

                raw, scaled = read_process_value(plc)

                attributes = {
                    "raw_value": raw,
                    "index_group": f"0x{INDEX_GROUP:X}",
                    "index_offset": f"0x{INDEX_OFFSET:X}",
                    "ads_port": PLC_ADS_PORT,
                    "data_type": ADS_DATA_TYPE,
                    "scale": VALUE_SCALE,
                    "offset_adjustment": VALUE_OFFSET,
                    "state_probe_ok": state_ok,
                    "device_info_probe_ok": info_ok,
                    "ads_state": repr(state),
                    "device_info": repr(device_info),
                    "explicit_local_route": ADD_LOCAL_ROUTE,
                }

                client.publish(STATE_TOPIC, str(scaled), qos=1, retain=True)
                client.publish(RAW_TOPIC, json.dumps(attributes), qos=1, retain=True)
                client.publish(AVAILABILITY_TOPIC, "online", qos=1, retain=True)

            except Exception as err:
                LOGGER.exception(
                    "Direct ADS memory read failed (%s: %s)",
                    type(err).__name__,
                    err,
                )
                client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)

                if plc is not None:
                    try:
                        plc.close()
                    except Exception:
                        LOGGER.exception("Error while closing ADS connection")
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
                LOGGER.exception("Error during final ADS close")

        client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    sys.exit(main())
