from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt
import pyads

VERSION = "1.0.0"

PLC_IP = os.environ["PLC_IP"]
PLC_AMS_NET_ID = os.environ["PLC_AMS_NET_ID"]
LOCAL_AMS_NET_ID = os.environ["LOCAL_AMS_NET_ID"]
PLC_ADS_PORT = int(os.environ["PLC_ADS_PORT"])

POLL_INTERVAL = int(os.environ["POLL_INTERVAL"])
RECONNECT_DELAY = int(os.environ["RECONNECT_DELAY"])
PUBLISH_HEARTBEAT = int(os.environ["PUBLISH_HEARTBEAT"])
ADD_LOCAL_ROUTE = os.environ.get("ADD_LOCAL_ROUTE", "true").lower() == "true"

READ_MODE = os.environ.get("READ_MODE", "symbol").lower()
ADS_SYMBOL = os.environ["ADS_SYMBOL"]
SYMBOL_DATA_TYPE = os.environ["SYMBOL_DATA_TYPE"].upper()

FALLBACK_DIRECT_READ = os.environ.get("FALLBACK_DIRECT_READ", "true").lower() == "true"
INDEX_GROUP_TEXT = os.environ["INDEX_GROUP"]
INDEX_OFFSET_TEXT = os.environ["INDEX_OFFSET"]
INDEX_GROUP = int(INDEX_GROUP_TEXT, 0)
INDEX_OFFSET = int(INDEX_OFFSET_TEXT, 0)
DIRECT_DATA_TYPE = os.environ["DIRECT_DATA_TYPE"].upper()

VALUE_SCALE = float(os.environ["VALUE_SCALE"])
VALUE_OFFSET = float(os.environ["VALUE_OFFSET"])
VALUE_PRECISION = int(os.environ["VALUE_PRECISION"])

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

for dtype in (SYMBOL_DATA_TYPE, DIRECT_DATA_TYPE):
    if dtype not in ADS_TYPES:
        raise RuntimeError(f"Unsupported ADS data type: {dtype}")

DISCOVERY_TOPIC = f"homeassistant/sensor/beckhoff_ads/{ENTITY_ID}/config"
STATE_TOPIC = f"beckhoff_ads/{ENTITY_ID}/state"
ATTR_TOPIC = f"beckhoff_ads/{ENTITY_ID}/attributes"
AVAILABILITY_TOPIC = f"beckhoff_ads/{ENTITY_ID}/availability"

stop_requested = False
mqtt_connected = threading.Event()
route_configured = False


def stop_handler(_signum: int, _frame: Any) -> None:
    global stop_requested
    stop_requested = True


signal.signal(signal.SIGTERM, stop_handler)
signal.signal(signal.SIGINT, stop_handler)


def on_connect(client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any = None) -> None:
    if int(reason_code) == 0:
        LOGGER.info("MQTT connected to %s:%s", MQTT_HOST, MQTT_PORT)
        mqtt_connected.set()
    else:
        LOGGER.error("MQTT connection failed, reason=%s", reason_code)


def on_disconnect(client: mqtt.Client, userdata: Any, disconnect_flags: Any, reason_code: Any, properties: Any = None) -> None:
    mqtt_connected.clear()
    if not stop_requested:
        LOGGER.warning("MQTT disconnected, reason=%s", reason_code)


def create_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="beckhoff_ads_gateway",
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    client.will_set(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()

    if not mqtt_connected.wait(timeout=15):
        raise RuntimeError("MQTT broker connection timeout")

    return client


def publish_discovery(client: mqtt.Client) -> None:
    discovery = {
        "name": ENTITY_NAME,
        "unique_id": f"beckhoff_ads_{ENTITY_ID}",
        "object_id": ENTITY_ID,
        "state_topic": STATE_TOPIC,
        "availability_topic": AVAILABILITY_TOPIC,
        "payload_available": "online",
        "payload_not_available": "offline",
        "json_attributes_topic": ATTR_TOPIC,
        "unit_of_measurement": UNIT,
        "device_class": DEVICE_CLASS,
        "state_class": STATE_CLASS,
        "suggested_display_precision": VALUE_PRECISION,
        "device": {
            "identifiers": ["beckhoff_cx5000_ads"],
            "name": "Beckhoff CX5000",
            "manufacturer": "Beckhoff",
            "model": "TwinCAT 2 / TcBA",
        },
        "origin": {
            "name": "Beckhoff ADS Gateway",
            "sw_version": VERSION,
            "support_url": "https://github.com/timojtuominen-ai/homeassistant-floorplan",
        },
    }
    info = client.publish(DISCOVERY_TOPIC, json.dumps(discovery), qos=1, retain=True)
    info.wait_for_publish(timeout=5)
    LOGGER.info("MQTT Discovery published: %s", DISCOVERY_TOPIC)


def configure_local_ads_once() -> None:
    global route_configured
    if route_configured:
        return

    port = pyads.open_port()
    try:
        pyads.set_local_address(LOCAL_AMS_NET_ID)
        LOGGER.info("Local AMS Net ID: %s", pyads.get_local_address())

        if ADD_LOCAL_ROUTE:
            pyads.add_route(PLC_AMS_NET_ID, PLC_IP)
            LOGGER.info("Local ADS route configured: %s -> %s", PLC_AMS_NET_ID, PLC_IP)
    finally:
        pyads.close_port()

    route_configured = True


def open_plc() -> pyads.Connection:
    connection = pyads.Connection(PLC_AMS_NET_ID, PLC_ADS_PORT, PLC_IP)
    connection.open()
    LOGGER.info(
        "ADS connected: %s:%s via %s (local %s)",
        PLC_AMS_NET_ID,
        PLC_ADS_PORT,
        PLC_IP,
        connection.get_local_address(),
    )
    return connection


def read_symbol(connection: pyads.Connection) -> Any:
    return connection.read_by_name(ADS_SYMBOL, ADS_TYPES[SYMBOL_DATA_TYPE])


def read_direct(connection: pyads.Connection) -> Any:
    return connection.read(INDEX_GROUP, INDEX_OFFSET, ADS_TYPES[DIRECT_DATA_TYPE])


def read_value(connection: pyads.Connection) -> tuple[Any, float, str]:
    if READ_MODE == "direct":
        raw = read_direct(connection)
        source = f"direct {INDEX_GROUP_TEXT}/{INDEX_OFFSET_TEXT}"
    else:
        try:
            raw = read_symbol(connection)
            source = f"symbol {ADS_SYMBOL}"
        except Exception as err:
            if not FALLBACK_DIRECT_READ:
                raise
            LOGGER.warning(
                "Symbol read failed (%s). Trying verified direct TcBA address.",
                err,
            )
            raw = read_direct(connection)
            source = f"direct fallback {INDEX_GROUP_TEXT}/{INDEX_OFFSET_TEXT}"

    value = round((float(raw) * VALUE_SCALE) + VALUE_OFFSET, VALUE_PRECISION)
    return raw, value, source


def publish_state(
    client: mqtt.Client,
    raw: Any,
    value: float,
    source: str,
) -> None:
    attributes = {
        "source": source,
        "raw_value": raw,
        "ads_port": PLC_ADS_PORT,
        "plc_ip": PLC_IP,
        "plc_ams_net_id": PLC_AMS_NET_ID,
        "gateway_version": VERSION,
        "read_only": True,
    }

    state_info = client.publish(STATE_TOPIC, str(value), qos=1, retain=True)
    attr_info = client.publish(ATTR_TOPIC, json.dumps(attributes), qos=1, retain=True)
    avail_info = client.publish(AVAILABILITY_TOPIC, "online", qos=1, retain=True)

    state_info.wait_for_publish(timeout=5)
    attr_info.wait_for_publish(timeout=5)
    avail_info.wait_for_publish(timeout=5)

    LOGGER.info("MQTT state published: %s = %s %s (%s)", ENTITY_ID, value, UNIT, source)


def close_plc(plc: pyads.Connection | None) -> None:
    if plc is None:
        return
    try:
        plc.close()
    except Exception:
        LOGGER.exception("Error while closing ADS connection")


def interruptible_sleep(seconds: int) -> None:
    for _ in range(seconds * 10):
        if stop_requested:
            return
        time.sleep(0.1)


def main() -> int:
    client = create_mqtt_client()
    publish_discovery(client)
    configure_local_ads_once()

    plc: pyads.Connection | None = None
    last_value: float | None = None
    last_publish = 0.0
    reconnects = 0

    try:
        while not stop_requested:
            try:
                if plc is None or not plc.is_open:
                    plc = open_plc()

                raw, value, source = read_value(plc)
                now = time.monotonic()

                changed = last_value is None or value != last_value
                heartbeat_due = (now - last_publish) >= PUBLISH_HEARTBEAT

                if changed or heartbeat_due:
                    publish_state(client, raw, value, source)
                    last_value = value
                    last_publish = now
                else:
                    LOGGER.debug("ADS value unchanged: %s %s", value, UNIT)

                interruptible_sleep(POLL_INTERVAL)

            except Exception as err:
                reconnects += 1
                LOGGER.exception(
                    "ADS read/connection failed (%s: %s). Reconnect #%s in %ss.",
                    type(err).__name__,
                    err,
                    reconnects,
                    RECONNECT_DELAY,
                )
                client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
                close_plc(plc)
                plc = None
                interruptible_sleep(RECONNECT_DELAY)

        return 0

    finally:
        close_plc(plc)
        try:
            client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True).wait_for_publish(timeout=3)
        except Exception:
            pass
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    sys.exit(main())
