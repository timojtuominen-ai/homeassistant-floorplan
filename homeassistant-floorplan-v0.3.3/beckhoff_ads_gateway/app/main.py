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
LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG").upper()

LIST_SYMBOLS = os.environ.get("LIST_SYMBOLS", "true").lower() == "true"
SYMBOL_FILTER = os.environ.get("SYMBOL_FILTER", "").strip().lower()
MAX_SYMBOLS = int(os.environ.get("MAX_SYMBOLS", "500"))

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

DISCOVERY_TOPIC = f"homeassistant/sensor/beckhoff_ads/{ENTITY_ID}/config"
STATE_TOPIC = f"beckhoff_ads/{ENTITY_ID}/state"
AVAILABILITY_TOPIC = "beckhoff_ads/status"

SYSTEM_SERVICE_PORT = 10000
stop_requested = False
symbol_browser_completed = False


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
            "sw_version": "0.3.3",
        },
    }

    client.publish(DISCOVERY_TOPIC, json.dumps(discovery), qos=1, retain=True)
    client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
    LOGGER.info("MQTT discovery published")
    return client


def configure_local_ads() -> None:
    LOGGER.info("Opening local ADS router port")
    port = pyads.open_port()
    try:
        pyads.set_local_address(LOCAL_AMS_NET_ID)
        local = pyads.get_local_address()
        LOGGER.info("Requested local AMS Net ID: %s", LOCAL_AMS_NET_ID)
        LOGGER.info("Actual local ADS address: %s", local)
    finally:
        pyads.close_port()


def test_ads_port(port: int, label: str) -> bool:
    LOGGER.info("Testing %s ADS port %s", label, port)
    connection = pyads.Connection(PLC_AMS_NET_ID, port, PLC_IP)
    try:
        connection.open()
        LOGGER.info("%s connection object opened", label)
        LOGGER.info("%s local address: %s", label, connection.get_local_address())
        info = connection.read_device_info()
        LOGGER.info("%s read_device_info succeeded: %r", label, info)
        return True
    except Exception as err:
        LOGGER.exception(
            "%s ADS test failed (%s: %s)",
            label,
            type(err).__name__,
            err,
        )
        return False
    finally:
        try:
            connection.close()
        except Exception:
            LOGGER.exception("Failed to close %s connection", label)


def connect_plc() -> pyads.Connection:
    connection = pyads.Connection(PLC_AMS_NET_ID, PLC_ADS_PORT, PLC_IP)
    connection.open()
    LOGGER.info("PLC connection object opened on ADS port %s", PLC_ADS_PORT)
    LOGGER.info("PLC connection local address: %s", connection.get_local_address())
    return connection


def browse_symbols(connection: pyads.Connection) -> None:
    global symbol_browser_completed

    if symbol_browser_completed or not LIST_SYMBOLS:
        return

    LOGGER.info("=== ADS SYMBOL BROWSER START ===")
    LOGGER.info(
        "Requesting published PLC symbols; filter=%r, maximum=%s",
        SYMBOL_FILTER,
        MAX_SYMBOLS,
    )

    symbols = connection.get_all_symbols()
    LOGGER.info("PLC returned %s published symbols", len(symbols))

    matched = 0
    for symbol in symbols:
        name = symbol.name or ""
        symtype = symbol.symbol_type or ""
        comment = symbol.comment or ""

        searchable = f"{name} {symtype} {comment}".lower()
        if SYMBOL_FILTER and SYMBOL_FILTER not in searchable:
            continue

        LOGGER.info(
            "ADS_SYMBOL name=%r type=%r index_group=%s index_offset=%s comment=%r",
            name,
            symtype,
            symbol.index_group,
            symbol.index_offset,
            comment,
        )
        matched += 1
        if matched >= MAX_SYMBOLS:
            LOGGER.warning("Symbol output stopped at max_symbols=%s", MAX_SYMBOLS)
            break

    LOGGER.info(
        "=== ADS SYMBOL BROWSER RESULT: total=%s matched=%s ===",
        len(symbols),
        matched,
    )
    symbol_browser_completed = True


def read_symbol(connection: pyads.Connection) -> Any:
    LOGGER.info("Reading configured symbol: %s as %s", ADS_SYMBOL, ADS_DATA_TYPE)
    value = connection.read_by_name(ADS_SYMBOL, ADS_TYPES[ADS_DATA_TYPE])
    LOGGER.info("Configured symbol read succeeded: %s = %r", ADS_SYMBOL, value)
    return value


def main() -> int:
    client = create_mqtt_client()
    plc: pyads.Connection | None = None

    configure_local_ads()

    LOGGER.info("=== ADS DIAGNOSTIC START ===")
    system_ok = test_ads_port(SYSTEM_SERVICE_PORT, "System service")
    plc_ok = test_ads_port(PLC_ADS_PORT, "PLC runtime")
    LOGGER.info(
        "=== ADS DIAGNOSTIC RESULT: system_service=%s, plc_runtime=%s ===",
        system_ok,
        plc_ok,
    )

    try:
        while not stop_requested:
            try:
                if plc is None or not plc.is_open:
                    plc = connect_plc()

                browse_symbols(plc)
                value = read_symbol(plc)

                client.publish(STATE_TOPIC, str(value), qos=1, retain=True)
                client.publish(AVAILABILITY_TOPIC, "online", qos=1, retain=True)

            except Exception as err:
                LOGGER.exception(
                    "ADS operation failed (%s: %s)",
                    type(err).__name__,
                    err,
                )
                client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)

                if plc is not None:
                    try:
                        plc.close()
                    except Exception:
                        LOGGER.exception("Error while closing PLC connection")
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
