from __future__ import annotations
import json, logging, os, signal, threading, time, queue
from typing import Any
import paho.mqtt.client as mqtt
import pyads

VERSION = "1.7.0"
PLC_IP = os.environ["PLC_IP"]
PLC_AMS_NET_ID = os.environ["PLC_AMS_NET_ID"]
LOCAL_AMS_NET_ID = os.environ["LOCAL_AMS_NET_ID"]
PLC_ADS_PORT = int(os.environ["PLC_ADS_PORT"])
POLL_INTERVAL = int(os.environ["POLL_INTERVAL"])
LIGHT_POLL_INTERVAL = int(os.environ.get("LIGHT_POLL_INTERVAL", "1"))
BINARY_POLL_INTERVAL = int(os.environ.get("BINARY_POLL_INTERVAL", "1"))
RECONNECT_DELAY = int(os.environ["RECONNECT_DELAY"])
PUBLISH_HEARTBEAT = int(os.environ["PUBLISH_HEARTBEAT"])
ADD_LOCAL_ROUTE = os.environ.get("ADD_LOCAL_ROUTE", "true").lower() == "true"
SENSORS_JSON = os.environ["SENSORS_JSON"]
LIGHTS_JSON = os.environ.get("LIGHTS_JSON", "[]")
BINARY_SENSORS_JSON = os.environ.get("BINARY_SENSORS_JSON", "[]")
TIMED_OUTPUTS_JSON = os.environ.get("TIMED_OUTPUTS_JSON", "[]")
ROOMS_JSON = os.environ.get("ROOMS_JSON", "[]")
SCAN_HVAC_STATES = os.environ.get("SCAN_HVAC_STATES", "false").lower() == "true"
SCAN_START_INDEX = int(os.environ.get("SCAN_START_INDEX", "0"))
SCAN_END_INDEX = int(os.environ.get("SCAN_END_INDEX", "31"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
MQTT_HOST = os.environ["MQTT_HOST"]
MQTT_PORT = int(os.environ["MQTT_PORT"])
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
LOGGER = logging.getLogger("beckhoff_ads_gateway")
ADS_TYPES = {"BOOL":pyads.PLCTYPE_BOOL,"BYTE":pyads.PLCTYPE_BYTE,"WORD":pyads.PLCTYPE_WORD,"DWORD":pyads.PLCTYPE_DWORD,"INT":pyads.PLCTYPE_INT,"UINT":pyads.PLCTYPE_UINT,"DINT":pyads.PLCTYPE_DINT,"UDINT":pyads.PLCTYPE_UDINT,"REAL":pyads.PLCTYPE_REAL,"LREAL":pyads.PLCTYPE_LREAL}


def load_array(raw: str, label: str):
    try:
        value = json.loads(raw)
        if not isinstance(value, list):
            raise ValueError(f"{label} must contain a JSON array")
        return value
    except Exception as err:
        raise RuntimeError(f"Invalid {label}: {err}") from err

SENSORS = load_array(SENSORS_JSON, "sensors_json")
LIGHTS = load_array(LIGHTS_JSON, "lights_json")
BINARY_SENSORS = load_array(BINARY_SENSORS_JSON, "binary_sensors_json")
TIMED_OUTPUTS = load_array(TIMED_OUTPUTS_JSON, "timed_outputs_json")
ROOMS = load_array(ROOMS_JSON, "rooms_json")
if not SENSORS:
    raise RuntimeError("sensors_json must not be empty")

for sensor in SENSORS:
    for key in ("id", "name", "symbol"):
        if not sensor.get(key):
            raise RuntimeError(f"Sensor missing required field {key}: {sensor}")
    dtype = sensor.get("type", "LREAL").upper()
    if dtype not in ADS_TYPES:
        raise RuntimeError(f"Unsupported data type {dtype} for {sensor['id']}")

for light in LIGHTS:
    for key in ("id", "name", "command_on_symbol", "command_off_symbol", "state_symbol"):
        if not light.get(key):
            raise RuntimeError(f"Light missing required field {key}: {light}")

for binary_sensor in BINARY_SENSORS:
    for key in ("id", "name", "symbol"):
        if not binary_sensor.get(key):
            raise RuntimeError(f"Binary sensor missing required field {key}: {binary_sensor}")

for timed_output in TIMED_OUTPUTS:
    for key in ("id", "name", "command_on_symbol", "command_off_symbol", "state_symbol"):
        if not timed_output.get(key):
            raise RuntimeError(f"Timed output missing required field {key}: {timed_output}")
    if int(timed_output.get("duration_s", 0)) <= 0:
        raise RuntimeError(f"Timed output duration_s must be > 0: {timed_output}")

LIGHT_BY_ID = {light["id"]: light for light in LIGHTS}
for room in ROOMS:
    for key in ("id", "name", "lights"):
        if key not in room:
            raise RuntimeError(f"Room missing required field {key}: {room}")
    missing = [lid for lid in room["lights"] if lid not in LIGHT_BY_ID]
    if missing:
        raise RuntimeError(f"Room {room['id']} has unknown lights: {missing}")

command_queue = queue.Queue()
timed_command_queue = queue.Queue()
TIMED_STATE_FILE = "/data/timed_outputs_state.json"
stop_requested = False
mqtt_connected = threading.Event()
route_configured = False


def stop_handler(_s: int, _f: Any) -> None:
    global stop_requested
    stop_requested = True

signal.signal(signal.SIGTERM, stop_handler)
signal.signal(signal.SIGINT, stop_handler)


def device_block():
    return {
        "identifiers": ["beckhoff_cx5000_ads"],
        "name": "Beckhoff CX5000",
        "manufacturer": "Beckhoff",
        "model": "TwinCAT 2 / TcBA",
    }


def origin_block():
    return {
        "name": "Beckhoff ADS Gateway",
        "sw_version": VERSION,
        "support_url": "https://github.com/timojtuominen-ai/homeassistant-floorplan",
    }


def sensor_topics(sensor):
    sid = sensor["id"]
    return (
        f"homeassistant/sensor/beckhoff_ads/{sid}/config",
        f"beckhoff_ads/{sid}/state",
        f"beckhoff_ads/{sid}/attributes",
        f"beckhoff_ads/{sid}/availability",
    )


def light_topics(light):
    lid = light["id"]
    return (
        f"homeassistant/light/beckhoff_ads/{lid}/config",
        f"beckhoff_ads/light/{lid}/state",
        f"beckhoff_ads/light/{lid}/set",
        f"beckhoff_ads/light/{lid}/availability",
    )


def binary_sensor_topics(binary_sensor):
    bid = binary_sensor["id"]
    return (
        f"homeassistant/binary_sensor/beckhoff_ads/{bid}/config",
        f"beckhoff_ads/binary/{bid}/state",
        f"beckhoff_ads/binary/{bid}/attributes",
        f"beckhoff_ads/binary/{bid}/availability",
    )



def timed_output_topics(timed_output):
    tid = timed_output["id"]
    return (
        f"homeassistant/switch/beckhoff_ads/{tid}/config",
        f"beckhoff_ads/timed/{tid}/state",
        f"beckhoff_ads/timed/{tid}/set",
        f"beckhoff_ads/timed/{tid}/availability",
    )

def room_topics(room):
    rid = room["id"]
    return (
        f"homeassistant/sensor/beckhoff_ads/{rid}_valot_paalla/config",
        f"beckhoff_ads/room/{rid}/lights_on/state",
        f"beckhoff_ads/room/{rid}/lights_on/attributes",
        f"beckhoff_ads/room/{rid}/lights_on/availability",
    )


def on_connect(client, userdata, flags, reason_code, properties=None):
    if bool(getattr(reason_code, "is_failure", False)):
        LOGGER.error("MQTT connection failed: %s", reason_code)
        return
    LOGGER.info("MQTT connected to %s:%s (reason=%s)", MQTT_HOST, MQTT_PORT, reason_code)
    mqtt_connected.set()
    for light in LIGHTS:
        client.subscribe(light_topics(light)[2], qos=1)
    for timed_output in TIMED_OUTPUTS:
        client.subscribe(timed_output_topics(timed_output)[2], qos=1)
    LOGGER.info("MQTT subscribed to %d light and %d timed-output command topics", len(LIGHTS), len(TIMED_OUTPUTS))


def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    mqtt_connected.clear()
    if not stop_requested:
        LOGGER.warning("MQTT disconnected: %s", reason_code)


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="ignore").strip().upper()
    for light in LIGHTS:
        if msg.topic == light_topics(light)[2]:
            if payload in ("ON", "OFF"):
                command_queue.put((light, payload))
                LOGGER.info("MQTT light command queued: %s -> %s", light["id"], payload)
            else:
                LOGGER.warning("Ignoring invalid light command for %s: %r", light["id"], payload)
            return
    for timed_output in TIMED_OUTPUTS:
        if msg.topic == timed_output_topics(timed_output)[2]:
            if payload in ("ON", "OFF"):
                timed_command_queue.put((timed_output, payload))
                LOGGER.info("MQTT timed-output command queued: %s -> %s", timed_output["id"], payload)
            else:
                LOGGER.warning("Ignoring invalid timed-output command for %s: %r", timed_output["id"], payload)
            return


def mqtt_client():
    c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="beckhoff_ads_gateway")
    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    c.on_message = on_message
    if MQTT_USERNAME:
        c.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    c.loop_start()
    if not mqtt_connected.wait(15):
        raise RuntimeError("MQTT broker connection timeout")
    return c


def publish_sensor_discovery(c, sensor):
    discovery_topic, state_topic, attr_topic, avail_topic = sensor_topics(sensor)
    payload = {
        "name": sensor["name"],
        "unique_id": f"beckhoff_ads_{sensor['id']}",
        "state_topic": state_topic,
        "availability_topic": avail_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "json_attributes_topic": attr_topic,
        "unit_of_measurement": sensor.get("unit", "°C"),
        "device_class": sensor.get("device_class", "temperature"),
        "state_class": sensor.get("state_class", "measurement"),
        "suggested_display_precision": int(sensor.get("precision", 1)),
        "device": device_block(),
        "origin": origin_block(),
    }
    c.publish(discovery_topic, json.dumps(payload), qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT Discovery published: %s -> %s", sensor["id"], sensor["symbol"])


DEPRECATED_LIGHT_IDS = [
    "oh_pihan_puolen_valot",
    "oh_porrasaukko_valo",
]


def remove_deprecated_light_discovery(c):
    for lid in DEPRECATED_LIGHT_IDS:
        topic = f"homeassistant/light/beckhoff_ads/{lid}/config"
        c.publish(topic, "", qos=1, retain=True).wait_for_publish(timeout=5)
        LOGGER.info("Removed deprecated MQTT Light Discovery: %s", lid)


def publish_light_discovery(c, light):
    discovery_topic, state_topic, command_topic, avail_topic = light_topics(light)
    payload = {
        "name": light["name"],
        "unique_id": f"beckhoff_ads_light_{light['id']}",
        "default_entity_id": f"light.{light['id']}",
        "state_topic": state_topic,
        "command_topic": command_topic,
        "availability_topic": avail_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "payload_on": "ON",
        "payload_off": "OFF",
        "state_on": "ON",
        "state_off": "OFF",
        "optimistic": False,
        "icon": "mdi:lightbulb",
        "device": device_block(),
        "origin": origin_block(),
    }
    c.publish(discovery_topic, json.dumps(payload), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT Light Discovery published: %s", light["id"])


DEPRECATED_BINARY_SENSOR_IDS = [
    "vuotovahti_keittio",
    "vuotovahti_ylakerran_wc",
    "vuotovahti_alakerran_wc",
    "vuotovahti_tekninentila",
]


def remove_deprecated_binary_sensor_discovery(c):
    for bid in DEPRECATED_BINARY_SENSOR_IDS:
        topic = f"homeassistant/binary_sensor/beckhoff_ads/{bid}/config"
        c.publish(topic, "", qos=1, retain=True).wait_for_publish(timeout=5)
        LOGGER.info("Removed deprecated MQTT Binary Sensor Discovery: %s", bid)


def publish_binary_sensor_discovery(c, binary_sensor):
    discovery_topic, state_topic, attr_topic, avail_topic = binary_sensor_topics(binary_sensor)
    payload = {
        "name": binary_sensor["name"],
        "unique_id": f"beckhoff_ads_binary_{binary_sensor['id']}",
        "default_entity_id": f"binary_sensor.{binary_sensor['id']}",
        "state_topic": state_topic,
        "availability_topic": avail_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "payload_on": "ON",
        "payload_off": "OFF",
        "json_attributes_topic": attr_topic,
        "device_class": binary_sensor.get("device_class"),
        "device": device_block(),
        "origin": origin_block(),
    }
    c.publish(discovery_topic, json.dumps(payload), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT Binary Sensor Discovery published: %s -> %s", binary_sensor["id"], binary_sensor["symbol"])



def publish_timed_output_discovery(c, timed_output):
    discovery_topic, state_topic, command_topic, avail_topic = timed_output_topics(timed_output)
    payload = {
        "name": timed_output["name"],
        "unique_id": f"beckhoff_ads_timed_{timed_output['id']}",
        "default_entity_id": f"switch.{timed_output['id']}",
        "state_topic": state_topic,
        "command_topic": command_topic,
        "availability_topic": avail_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "payload_on": "ON",
        "payload_off": "OFF",
        "state_on": "ON",
        "state_off": "OFF",
        "optimistic": False,
        "icon": timed_output.get("icon", "mdi:timer"),
        "device": device_block(),
        "origin": origin_block(),
    }
    c.publish(discovery_topic, json.dumps(payload), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT Timed Output Discovery published: %s", timed_output["id"])

def publish_room_discovery(c, room):
    discovery_topic, state_topic, attr_topic, avail_topic = room_topics(room)
    total = len(room["lights"])
    payload = {
        "name": room["name"],
        "unique_id": f"beckhoff_ads_room_{room['id']}_lights_on",
        "default_entity_id": f"sensor.{room['id']}_valot_paalla",
        "state_topic": state_topic,
        "availability_topic": avail_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "json_attributes_topic": attr_topic,
        "unit_of_measurement": f"/ {total}",
        "icon": "mdi:lightbulb-group",
        "device": device_block(),
        "origin": origin_block(),
    }
    c.publish(discovery_topic, json.dumps(payload), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT room light-count Discovery published: %s (0..%d)", room["id"], total)


def configure_route_once():
    global route_configured
    if route_configured:
        return
    port = pyads.open_port()
    try:
        pyads.set_local_address(LOCAL_AMS_NET_ID)
        LOGGER.info("Local AMS Net ID: %s", pyads.get_local_address())
        if ADD_LOCAL_ROUTE:
            pyads.add_route(PLC_AMS_NET_ID, PLC_IP)
            LOGGER.info("Local ADS route configured")
    finally:
        pyads.close_port()
    route_configured = True


def open_plc():
    plc = pyads.Connection(PLC_AMS_NET_ID, PLC_ADS_PORT, PLC_IP)
    plc.open()
    LOGGER.info("ADS connected: %s:%s via %s", PLC_AMS_NET_ID, PLC_ADS_PORT, PLC_IP)
    return plc


def pulse_light_command(plc, light, command):
    symbol = light["command_on_symbol"] if command == "ON" else light["command_off_symbol"]
    opposite = light["command_off_symbol"] if command == "ON" else light["command_on_symbol"]
    pulse_ms = max(50, int(light.get("pulse_ms", 200)))
    plc.write_by_name(opposite, False, pyads.PLCTYPE_BOOL)
    plc.write_by_name(symbol, False, pyads.PLCTYPE_BOOL)
    time.sleep(0.05)
    plc.write_by_name(symbol, True, pyads.PLCTYPE_BOOL)
    readback_high = bool(plc.read_by_name(symbol, pyads.PLCTYPE_BOOL))
    LOGGER.info("TcBA command asserted: %s -> %s, symbol=%s, readback=%s", light["id"], command, symbol, readback_high)
    time.sleep(pulse_ms / 1000.0)
    plc.write_by_name(symbol, False, pyads.PLCTYPE_BOOL)
    readback_low = bool(plc.read_by_name(symbol, pyads.PLCTYPE_BOOL))
    LOGGER.info("TcBA light pulse completed: %s -> %s (%d ms), cleared_readback=%s", light["id"], command, pulse_ms, readback_low)


def process_light_commands(plc):
    processed = 0
    while processed < 10:
        try:
            light, command = command_queue.get_nowait()
        except queue.Empty:
            break
        pulse_light_command(plc, light, command)
        processed += 1



def load_timed_expiries():
    try:
        with open(TIMED_STATE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        valid_ids = {x["id"] for x in TIMED_OUTPUTS}
        return {k: float(v) for k, v in raw.items() if k in valid_ids and isinstance(v, (int, float))}
    except FileNotFoundError:
        return {}
    except Exception as err:
        LOGGER.warning("Could not load timed-output state: %s", err)
        return {}


def save_timed_expiries(expiries):
    try:
        os.makedirs(os.path.dirname(TIMED_STATE_FILE), exist_ok=True)
        tmp = TIMED_STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(expiries, f)
        os.replace(tmp, TIMED_STATE_FILE)
    except Exception as err:
        LOGGER.error("Could not save timed-output state: %s", err)


def pulse_timed_output_command(plc, timed_output, command):
    symbol = timed_output["command_on_symbol"] if command == "ON" else timed_output["command_off_symbol"]
    opposite = timed_output["command_off_symbol"] if command == "ON" else timed_output["command_on_symbol"]
    pulse_ms = max(50, int(timed_output.get("pulse_ms", 200)))
    asserted = False
    try:
        plc.write_by_name(opposite, False, pyads.PLCTYPE_BOOL)
        plc.write_by_name(symbol, False, pyads.PLCTYPE_BOOL)
        time.sleep(0.05)
        plc.write_by_name(symbol, True, pyads.PLCTYPE_BOOL)
        asserted = True
        readback_high = bool(plc.read_by_name(symbol, pyads.PLCTYPE_BOOL))
        LOGGER.info("TcBA timed-output command asserted: %s -> %s, symbol=%s, readback=%s", timed_output["id"], command, symbol, readback_high)
        time.sleep(pulse_ms / 1000.0)
    finally:
        if asserted:
            try:
                plc.write_by_name(symbol, False, pyads.PLCTYPE_BOOL)
                readback_low = bool(plc.read_by_name(symbol, pyads.PLCTYPE_BOOL))
                LOGGER.info("TcBA timed-output pulse completed: %s -> %s (%d ms), cleared_readback=%s", timed_output["id"], command, pulse_ms, readback_low)
            except Exception as err:
                LOGGER.error("Failed to clear timed-output command pulse %s (%s): %s", timed_output["id"], symbol, err)
                raise


def process_timed_output_commands(plc, expiries):
    processed = 0
    changed_expiries = False
    while processed < 10:
        try:
            timed_output, command = timed_command_queue.get_nowait()
        except queue.Empty:
            break
        pulse_timed_output_command(plc, timed_output, command)
        tid = timed_output["id"]
        if command == "ON":
            expiries[tid] = time.time() + int(timed_output.get("duration_s", 1800))
            LOGGER.info("Timed output %s armed for %d seconds", tid, int(timed_output.get("duration_s", 1800)))
        else:
            expiries.pop(tid, None)
            LOGGER.info("Timed output %s cancelled", tid)
        changed_expiries = True
        processed += 1
    if changed_expiries:
        save_timed_expiries(expiries)


def expire_timed_outputs(plc, expiries):
    now_wall = time.time()
    expired = []
    for timed_output in TIMED_OUTPUTS:
        tid = timed_output["id"]
        expiry = expiries.get(tid)
        if expiry is not None and now_wall >= expiry:
            LOGGER.info("Timed output expired: %s -> OFF", tid)
            pulse_timed_output_command(plc, timed_output, "OFF")
            expired.append(tid)
    if expired:
        for tid in expired:
            expiries.pop(tid, None)
        save_timed_expiries(expiries)


def read_timed_output_state(plc, timed_output):
    dtype = timed_output.get("state_type", "BOOL").upper()
    if dtype not in ADS_TYPES:
        raise RuntimeError(f"Unsupported timed-output state type {dtype} for {timed_output['id']}")
    raw = plc.read_by_name(timed_output["state_symbol"], ADS_TYPES[dtype])
    if dtype == "BOOL":
        return bool(raw), raw
    threshold = float(timed_output.get("state_threshold", 0.01))
    return float(raw) > threshold, float(raw)


def publish_timed_output_state(c, timed_output, state):
    _, state_topic, _, avail_topic = timed_output_topics(timed_output)
    text = "ON" if state else "OFF"
    c.publish(state_topic, text, qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT timed-output state published: %s = %s", timed_output["id"], text)

def read_sensor(plc, sensor):
    dtype = sensor.get("type", "LREAL").upper()
    raw = plc.read_by_name(sensor["symbol"], ADS_TYPES[dtype])
    value = round(float(raw) * float(sensor.get("scale", 1.0)) + float(sensor.get("offset", 0.0)), int(sensor.get("precision", 1)))
    return raw, value


def publish_sensor(c, sensor, raw, value):
    _, state_topic, attr_topic, avail_topic = sensor_topics(sensor)
    attrs = {"source": f"symbol {sensor['symbol']}", "raw_value": raw, "ads_port": PLC_ADS_PORT, "plc_ip": PLC_IP, "gateway_version": VERSION}
    c.publish(state_topic, str(value), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(attr_topic, json.dumps(attrs), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT state published: %s = %s %s", sensor["id"], value, sensor.get("unit", "°C"))


def read_binary_sensor(plc, binary_sensor):
    raw = bool(plc.read_by_name(binary_sensor["symbol"], pyads.PLCTYPE_BOOL))
    state = (not raw) if bool(binary_sensor.get("invert", False)) else raw
    return raw, state


def publish_binary_sensor(c, binary_sensor, raw, state):
    _, state_topic, attr_topic, avail_topic = binary_sensor_topics(binary_sensor)
    text = "ON" if state else "OFF"
    attrs = {
        "source": f"symbol {binary_sensor['symbol']}",
        "raw_value": raw,
        "inverted": bool(binary_sensor.get("invert", False)),
        "ads_port": PLC_ADS_PORT,
        "plc_ip": PLC_IP,
        "gateway_version": VERSION,
    }
    c.publish(state_topic, text, qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(attr_topic, json.dumps(attrs), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT binary state: %s = %s (raw=%s)", binary_sensor["id"], text, raw)


def read_light_state(plc, light):
    dtype = light.get("state_type", "BOOL").upper()
    if dtype not in ADS_TYPES:
        raise RuntimeError(f"Unsupported light state type {dtype} for {light['id']}")
    raw = plc.read_by_name(light["state_symbol"], ADS_TYPES[dtype])
    if dtype == "BOOL":
        return bool(raw), raw
    threshold = float(light.get("state_threshold", 0.01))
    return float(raw) > threshold, float(raw)


def publish_light_state(c, light, state):
    _, state_topic, _, avail_topic = light_topics(light)
    text = "ON" if state else "OFF"
    c.publish(state_topic, text, qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT light state published: %s = %s", light["id"], text)


def publish_room_state(c, room, light_states):
    _, state_topic, attr_topic, avail_topic = room_topics(room)
    total = len(room["lights"])
    on_ids = [lid for lid in room["lights"] if light_states.get(lid) is True]
    attrs = {"total": total, "on": len(on_ids), "on_lights": on_ids, "members": room["lights"], "gateway_version": VERSION}
    c.publish(state_topic, str(len(on_ids)), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(attr_topic, json.dumps(attrs), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT room light count: %s = %d / %d", room["id"], len(on_ids), total)


def scan_hvac(plc):
    if not SCAN_HVAC_STATES:
        return
    LOGGER.info("=== TcBA HVAC STATE SCAN %s..%s ===", SCAN_START_INDEX, SCAN_END_INDEX)
    for i in range(SCAN_START_INDEX, SCAN_END_INDEX + 1):
        symbol = f".arrHVACStates[{i}].lrActualValue"
        try:
            value = plc.read_by_name(symbol, pyads.PLCTYPE_LREAL)
            LOGGER.info("HVAC_SCAN index=%d symbol=%s value=%.3f", i, symbol, float(value))
        except Exception as err:
            LOGGER.debug("HVAC_SCAN index=%d failed: %s", i, err)
    LOGGER.info("=== TcBA HVAC STATE SCAN END ===")


def main():
    c = mqtt_client()
    remove_deprecated_light_discovery(c)
    remove_deprecated_binary_sensor_discovery(c)
    for sensor in SENSORS:
        publish_sensor_discovery(c, sensor)
    for light in LIGHTS:
        publish_light_discovery(c, light)
    for binary_sensor in BINARY_SENSORS:
        publish_binary_sensor_discovery(c, binary_sensor)
    for timed_output in TIMED_OUTPUTS:
        publish_timed_output_discovery(c, timed_output)
    for room in ROOMS:
        publish_room_discovery(c, room)

    configure_route_once()
    plc = None
    sensor_last = {}
    sensor_last_pub = {}
    light_states = {}
    light_last_pub = {}
    binary_states = {}
    binary_last_pub = {}
    timed_states = {}
    timed_last_pub = {}
    timed_expiries = load_timed_expiries()
    room_last = {}
    room_last_pub = {}
    reconnects = 0
    scanned = False
    next_sensor_poll = 0.0
    next_light_poll = 0.0
    next_binary_poll = 0.0
    next_timed_poll = 0.0

    try:
        while not stop_requested:
            try:
                if plc is None or not plc.is_open:
                    plc = open_plc()
                    scanned = False
                    next_sensor_poll = 0.0
                    next_light_poll = 0.0
                    next_binary_poll = 0.0
                    next_timed_poll = 0.0
                if not scanned:
                    scan_hvac(plc)
                    scanned = True

                process_light_commands(plc)
                process_timed_output_commands(plc, timed_expiries)
                expire_timed_outputs(plc, timed_expiries)
                now = time.monotonic()

                if now >= next_light_poll:
                    for light in LIGHTS:
                        try:
                            state, raw_state = read_light_state(plc, light)
                            lid = light["id"]
                            changed = lid not in light_states or light_states[lid] != state
                            heartbeat = now - light_last_pub.get(lid, 0) >= PUBLISH_HEARTBEAT
                            light_states[lid] = state
                            if changed or heartbeat:
                                publish_light_state(c, light, state)
                                LOGGER.info(
                                    "TcBA lighting state: %s raw=%.3f (%s)",
                                    lid, float(raw_state), light["state_symbol"]
                                )
                                light_last_pub[lid] = now
                        except Exception as err:
                            c.publish(light_topics(light)[3], "offline", qos=1, retain=True)
                            LOGGER.error("Light state read failed: %s (%s): %s", light["id"], light["state_symbol"], err)

                    for room in ROOMS:
                        valid = all(lid in light_states for lid in room["lights"])
                        if not valid:
                            continue
                        count = sum(1 for lid in room["lights"] if light_states[lid])
                        rid = room["id"]
                        changed = rid not in room_last or room_last[rid] != count
                        heartbeat = now - room_last_pub.get(rid, 0) >= PUBLISH_HEARTBEAT
                        if changed or heartbeat:
                            publish_room_state(c, room, light_states)
                            room_last[rid] = count
                            room_last_pub[rid] = now

                    next_light_poll = now + LIGHT_POLL_INTERVAL

                if now >= next_timed_poll:
                    for timed_output in TIMED_OUTPUTS:
                        try:
                            state, raw_state = read_timed_output_state(plc, timed_output)
                            tid = timed_output["id"]
                            previous = timed_states.get(tid)
                            # If this output was turned on outside this gateway, adopt it and ensure it
                            # still receives a finite 30-minute safety timeout.
                            if state and tid not in timed_expiries and (previous is None or previous is False):
                                timed_expiries[tid] = time.time() + int(timed_output.get("duration_s", 1800))
                                save_timed_expiries(timed_expiries)
                                LOGGER.info("Adopted externally active timed output %s for %d seconds", tid, int(timed_output.get("duration_s", 1800)))
                            elif (not state) and tid in timed_expiries:
                                timed_expiries.pop(tid, None)
                                save_timed_expiries(timed_expiries)

                            changed = tid not in timed_states or timed_states[tid] != state
                            heartbeat = now - timed_last_pub.get(tid, 0) >= PUBLISH_HEARTBEAT
                            timed_states[tid] = state
                            if changed or heartbeat:
                                publish_timed_output_state(c, timed_output, state)
                                LOGGER.info("TcBA timed-output state: %s raw=%s (%s)", tid, raw_state, timed_output["state_symbol"])
                                timed_last_pub[tid] = now
                        except Exception as err:
                            c.publish(timed_output_topics(timed_output)[3], "offline", qos=1, retain=True)
                            LOGGER.error("Timed-output state read failed: %s (%s): %s", timed_output["id"], timed_output["state_symbol"], err)
                    next_timed_poll = now + LIGHT_POLL_INTERVAL

                if now >= next_binary_poll:
                    for binary_sensor in BINARY_SENSORS:
                        try:
                            raw, state = read_binary_sensor(plc, binary_sensor)
                            bid = binary_sensor["id"]
                            changed = bid not in binary_states or binary_states[bid] != state
                            heartbeat = now - binary_last_pub.get(bid, 0) >= PUBLISH_HEARTBEAT
                            if changed or heartbeat:
                                publish_binary_sensor(c, binary_sensor, raw, state)
                                binary_states[bid] = state
                                binary_last_pub[bid] = now
                        except Exception as err:
                            c.publish(binary_sensor_topics(binary_sensor)[3], "offline", qos=1, retain=True)
                            LOGGER.error("Binary sensor read failed: %s (%s): %s", binary_sensor["id"], binary_sensor["symbol"], err)
                    next_binary_poll = now + BINARY_POLL_INTERVAL

                if now >= next_sensor_poll:
                    for sensor in SENSORS:
                        try:
                            raw, value = read_sensor(plc, sensor)
                            sid = sensor["id"]
                            changed = sid not in sensor_last or sensor_last[sid] != value
                            heartbeat = now - sensor_last_pub.get(sid, 0) >= PUBLISH_HEARTBEAT
                            if changed or heartbeat:
                                publish_sensor(c, sensor, raw, value)
                                sensor_last[sid] = value
                                sensor_last_pub[sid] = now
                        except Exception as err:
                            c.publish(sensor_topics(sensor)[3], "offline", qos=1, retain=True)
                            LOGGER.error("Sensor read failed: %s (%s): %s", sensor["id"], sensor["symbol"], err)
                    next_sensor_poll = now + POLL_INTERVAL

                time.sleep(0.20)

            except Exception as err:
                reconnects += 1
                LOGGER.exception("ADS connection failed: %s; reconnect #%d in %ds", err, reconnects, RECONNECT_DELAY)
                if plc:
                    try: plc.close()
                    except Exception: pass
                plc = None
                for light in LIGHTS:
                    try: c.publish(light_topics(light)[3], "offline", qos=1, retain=True)
                    except Exception: pass
                for room in ROOMS:
                    try: c.publish(room_topics(room)[3], "offline", qos=1, retain=True)
                    except Exception: pass
                for binary_sensor in BINARY_SENSORS:
                    try: c.publish(binary_sensor_topics(binary_sensor)[3], "offline", qos=1, retain=True)
                    except Exception: pass
                for timed_output in TIMED_OUTPUTS:
                    try: c.publish(timed_output_topics(timed_output)[3], "offline", qos=1, retain=True)
                    except Exception: pass
                for _ in range(RECONNECT_DELAY * 5):
                    if stop_requested: break
                    time.sleep(0.2)
        return 0
    finally:
        if plc:
            try: plc.close()
            except Exception: pass
        for sensor in SENSORS:
            try: c.publish(sensor_topics(sensor)[3], "offline", qos=1, retain=True)
            except Exception: pass
        for light in LIGHTS:
            try: c.publish(light_topics(light)[3], "offline", qos=1, retain=True)
            except Exception: pass
        for binary_sensor in BINARY_SENSORS:
            try: c.publish(binary_sensor_topics(binary_sensor)[3], "offline", qos=1, retain=True)
            except Exception: pass
        for timed_output in TIMED_OUTPUTS:
            try: c.publish(timed_output_topics(timed_output)[3], "offline", qos=1, retain=True)
            except Exception: pass
        for room in ROOMS:
            try: c.publish(room_topics(room)[3], "offline", qos=1, retain=True)
            except Exception: pass
        c.loop_stop()
        c.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
