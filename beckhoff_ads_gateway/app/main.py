from __future__ import annotations
import json, logging, os, signal, sys, threading, time, queue
from typing import Any
import paho.mqtt.client as mqtt
import pyads

VERSION = "1.3.0"
PLC_IP = os.environ["PLC_IP"]
PLC_AMS_NET_ID = os.environ["PLC_AMS_NET_ID"]
LOCAL_AMS_NET_ID = os.environ["LOCAL_AMS_NET_ID"]
PLC_ADS_PORT = int(os.environ["PLC_ADS_PORT"])
POLL_INTERVAL = int(os.environ["POLL_INTERVAL"])
RECONNECT_DELAY = int(os.environ["RECONNECT_DELAY"])
PUBLISH_HEARTBEAT = int(os.environ["PUBLISH_HEARTBEAT"])
ADD_LOCAL_ROUTE = os.environ.get("ADD_LOCAL_ROUTE", "true").lower() == "true"
SENSORS_JSON = os.environ["SENSORS_JSON"]
LIGHTS_JSON = os.environ.get("LIGHTS_JSON", "[]")
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

try:
    SENSORS = json.loads(SENSORS_JSON)
    if not isinstance(SENSORS, list) or not SENSORS:
        raise ValueError("sensors_json must contain a non-empty JSON array")
except Exception as err:
    raise RuntimeError(f"Invalid sensors_json: {err}") from err

for sensor in SENSORS:
    for key in ("id","name","symbol"):
        if not sensor.get(key): raise RuntimeError(f"Sensor missing required field {key}: {sensor}")
    dtype = sensor.get("type", "LREAL").upper()
    if dtype not in ADS_TYPES: raise RuntimeError(f"Unsupported data type {dtype} for {sensor['id']}")

try:
    LIGHTS = json.loads(LIGHTS_JSON)
    if not isinstance(LIGHTS, list):
        raise ValueError("lights_json must contain a JSON array")
except Exception as err:
    raise RuntimeError(f"Invalid lights_json: {err}") from err

for light in LIGHTS:
    for key in ("id", "name", "command_on_symbol", "command_off_symbol"):
        if not light.get(key):
            raise RuntimeError(f"Light missing required field {key}: {light}")

command_queue = queue.Queue()
stop_requested = False
mqtt_connected = threading.Event()
route_configured = False

def stop_handler(_s:int,_f:Any)->None:
    global stop_requested; stop_requested=True
signal.signal(signal.SIGTERM, stop_handler); signal.signal(signal.SIGINT, stop_handler)

def light_topics(light):
    lid = light["id"]
    return (
        f"homeassistant/light/beckhoff_ads/{lid}/config",
        f"beckhoff_ads/light/{lid}/state",
        f"beckhoff_ads/light/{lid}/set",
        f"beckhoff_ads/light/{lid}/availability",
    )

def on_connect(client, userdata, flags, reason_code, properties=None):
    if not bool(getattr(reason_code, "is_failure", False)):
        LOGGER.info("MQTT connected to %s:%s (reason=%s)", MQTT_HOST, MQTT_PORT, reason_code)
        mqtt_connected.set()
        for light in LIGHTS:
            client.subscribe(light_topics(light)[2], qos=1)
            LOGGER.info("MQTT light command subscribed: %s", light_topics(light)[2])
    else:
        LOGGER.error("MQTT connection failed: %s", reason_code)

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    mqtt_connected.clear()
    if not stop_requested: LOGGER.warning("MQTT disconnected: %s", reason_code)

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

def mqtt_client():
    c=mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="beckhoff_ads_gateway")
    c.on_connect=on_connect; c.on_disconnect=on_disconnect; c.on_message=on_message
    if MQTT_USERNAME: c.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    c.connect(MQTT_HOST, MQTT_PORT, keepalive=60); c.loop_start()
    if not mqtt_connected.wait(15): raise RuntimeError("MQTT broker connection timeout")
    return c

def topics(sensor):
    sid=sensor["id"]
    return (f"homeassistant/sensor/beckhoff_ads/{sid}/config", f"beckhoff_ads/{sid}/state", f"beckhoff_ads/{sid}/attributes", f"beckhoff_ads/{sid}/availability")

def publish_discovery(c, sensor):
    discovery_topic,state_topic,attr_topic,avail_topic=topics(sensor)
    payload={"name":sensor["name"],"unique_id":f"beckhoff_ads_{sensor['id']}","object_id":sensor["id"],"state_topic":state_topic,"availability_topic":avail_topic,"payload_available":"online","payload_not_available":"offline","json_attributes_topic":attr_topic,"unit_of_measurement":sensor.get("unit","°C"),"device_class":sensor.get("device_class","temperature"),"state_class":sensor.get("state_class","measurement"),"suggested_display_precision":int(sensor.get("precision",1)),"device":{"identifiers":["beckhoff_cx5000_ads"],"name":"Beckhoff CX5000","manufacturer":"Beckhoff","model":"TwinCAT 2 / TcBA"},"origin":{"name":"Beckhoff ADS Gateway","sw_version":VERSION,"support_url":"https://github.com/timojtuominen-ai/homeassistant-floorplan"}}
    c.publish(discovery_topic,json.dumps(payload),qos=1,retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT Discovery published: %s -> %s", sensor['id'], sensor['symbol'])

def publish_light_discovery(c, light):
    discovery_topic, state_topic, command_topic, avail_topic = light_topics(light)
    payload = {
        "name": light["name"],
        "unique_id": f"beckhoff_ads_light_{light['id']}",
        "object_id": light["id"],
        "state_topic": state_topic,
        "command_topic": command_topic,
        "availability_topic": avail_topic,
        "payload_on": "ON",
        "payload_off": "OFF",
        "state_on": "ON",
        "state_off": "OFF",
        "optimistic": False,
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
    c.publish(discovery_topic, json.dumps(payload), qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info(
        "MQTT Light Discovery published: %s (ON=%s, OFF=%s)",
        light["id"], light["command_on_symbol"], light["command_off_symbol"]
    )

def pulse_light_command(plc, light, command):
    symbol = light["command_on_symbol"] if command == "ON" else light["command_off_symbol"]
    pulse_ms = max(50, int(light.get("pulse_ms", 200)))

    # TcBA bOn/bOff are treated as momentary commands: FALSE -> TRUE -> FALSE.
    # We explicitly clear both first so no stale command can remain asserted.
    plc.write_by_name(light["command_on_symbol"], False, pyads.PLCTYPE_BOOL)
    plc.write_by_name(light["command_off_symbol"], False, pyads.PLCTYPE_BOOL)
    plc.write_by_name(symbol, True, pyads.PLCTYPE_BOOL)
    time.sleep(pulse_ms / 1000.0)
    plc.write_by_name(symbol, False, pyads.PLCTYPE_BOOL)
    LOGGER.info("TcBA light pulse sent: %s -> %s (%d ms)", light["id"], command, pulse_ms)

def read_light_state(plc, io_connections, light):
    state_symbol = light.get("state_symbol")
    if state_symbol:
        try:
            return bool(plc.read_by_name(state_symbol, pyads.PLCTYPE_BOOL)), f"symbol {state_symbol}"
        except Exception as err:
            LOGGER.debug("Light state symbol read failed for %s: %s", light["id"], err)

    ads_port = int(light.get("state_ads_port", 27908))
    ig = int(str(light["state_index_group"]), 0)
    io = int(str(light["state_index_offset"]), 0)

    conn = io_connections.get(ads_port)
    if conn is None or not conn.is_open:
        conn = pyads.Connection(PLC_AMS_NET_ID, ads_port, PLC_IP)
        conn.open()
        io_connections[ads_port] = conn
        LOGGER.info("ADS I/O state connection opened on port %s", ads_port)

    value = conn.read(ig, io, pyads.PLCTYPE_BOOL)
    return bool(value), f"ADS {ads_port} IG={hex(ig)} IO={hex(io)}"

def publish_light_state(c, light, state, source):
    _, state_topic, _, avail_topic = light_topics(light)
    text = "ON" if state else "OFF"
    c.publish(state_topic, text, qos=1, retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic, "online", qos=1, retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT light state published: %s = %s (%s)", light["id"], text, source)

def process_light_commands(plc):
    processed = 0
    while processed < 10:
        try:
            light, command = command_queue.get_nowait()
        except queue.Empty:
            break
        pulse_light_command(plc, light, command)
        processed += 1

def configure_route_once():
    global route_configured
    if route_configured:return
    port=pyads.open_port()
    try:
        pyads.set_local_address(LOCAL_AMS_NET_ID)
        LOGGER.info("Local AMS Net ID: %s", pyads.get_local_address())
        if ADD_LOCAL_ROUTE:
            pyads.add_route(PLC_AMS_NET_ID, PLC_IP); LOGGER.info("Local ADS route configured")
    finally: pyads.close_port()
    route_configured=True

def open_plc():
    p=pyads.Connection(PLC_AMS_NET_ID, PLC_ADS_PORT, PLC_IP); p.open()
    LOGGER.info("ADS connected: %s:%s via %s", PLC_AMS_NET_ID, PLC_ADS_PORT, PLC_IP); return p

def scan_hvac(plc):
    if not SCAN_HVAC_STATES:return
    LOGGER.info("=== TcBA HVAC STATE SCAN %s..%s ===", SCAN_START_INDEX, SCAN_END_INDEX)
    for i in range(SCAN_START_INDEX, SCAN_END_INDEX+1):
        symbol=f".arrHVACStates[{i}].lrActualValue"
        try:
            value=plc.read_by_name(symbol, pyads.PLCTYPE_LREAL)
            LOGGER.info("HVAC_SCAN index=%d symbol=%s value=%.3f", i, symbol, float(value))
        except Exception as err:
            LOGGER.debug("HVAC_SCAN index=%d failed: %s", i, err)
    LOGGER.info("=== TcBA HVAC STATE SCAN END ===")

def read_sensor(plc,sensor):
    dtype=sensor.get("type","LREAL").upper(); raw=plc.read_by_name(sensor["symbol"], ADS_TYPES[dtype])
    scale=float(sensor.get("scale",1.0)); offset=float(sensor.get("offset",0.0)); precision=int(sensor.get("precision",1))
    return raw, round(float(raw)*scale+offset, precision)

def publish_sensor(c,sensor,raw,value):
    _,state_topic,attr_topic,avail_topic=topics(sensor)
    attrs={"source":f"symbol {sensor['symbol']}","raw_value":raw,"ads_port":PLC_ADS_PORT,"plc_ip":PLC_IP,"gateway_version":VERSION,"read_only":True}
    c.publish(state_topic,str(value),qos=1,retain=True).wait_for_publish(timeout=5)
    c.publish(attr_topic,json.dumps(attrs),qos=1,retain=True).wait_for_publish(timeout=5)
    c.publish(avail_topic,"online",qos=1,retain=True).wait_for_publish(timeout=5)
    LOGGER.info("MQTT state published: %s = %s %s", sensor['id'], value, sensor.get('unit','°C'))

def sleep_i(sec):
    for _ in range(sec*10):
        if stop_requested:return
        time.sleep(.1)

def main():
    c=mqtt_client()
    for s in SENSORS: publish_discovery(c,s)
    for light in LIGHTS: publish_light_discovery(c, light)
    configure_route_once()
    plc=None; io_connections={}; last={}; last_pub={}; light_last={}; light_last_pub={}; reconnects=0; scanned=False
    try:
        while not stop_requested:
            try:
                if plc is None or not plc.is_open:
                    plc=open_plc(); scanned=False
                if not scanned:
                    scan_hvac(plc); scanned=True
                process_light_commands(plc)
                now=time.monotonic()
                for s in SENSORS:
                    try:
                        raw,val=read_sensor(plc,s)
                        sid=s['id']; changed=(sid not in last or last[sid]!=val); heartbeat=(now-last_pub.get(sid,0)>=PUBLISH_HEARTBEAT)
                        if changed or heartbeat:
                            publish_sensor(c,s,raw,val); last[sid]=val; last_pub[sid]=now
                    except Exception as err:
                        _,_,_,avail=topics(s); c.publish(avail,"offline",qos=1,retain=True)
                        LOGGER.error("Sensor read failed: %s (%s): %s", s['id'], s['symbol'], err)

                for light in LIGHTS:
                    try:
                        state, source = read_light_state(plc, io_connections, light)
                        lid = light["id"]
                        changed = lid not in light_last or light_last[lid] != state
                        heartbeat = now - light_last_pub.get(lid, 0) >= PUBLISH_HEARTBEAT
                        if changed or heartbeat:
                            publish_light_state(c, light, state, source)
                            light_last[lid] = state
                            light_last_pub[lid] = now
                    except Exception as err:
                        c.publish(light_topics(light)[3], "offline", qos=1, retain=True)
                        LOGGER.error("Light state read failed: %s: %s", light["id"], err)

                # Commands should feel responsive even though room temperatures are slow.
                # Sleep in one-second slices so queued light commands are processed promptly.
                remaining = POLL_INTERVAL
                while remaining > 0 and not stop_requested:
                    sleep_i(1)
                    remaining -= 1
                    if not stop_requested:
                        try:
                            process_light_commands(plc)
                        except Exception as err:
                            LOGGER.exception("Light command processing failed: %s", err)
            except Exception as err:
                reconnects+=1; LOGGER.exception("ADS connection failed: %s; reconnect #%d in %ds",err,reconnects,RECONNECT_DELAY)
                if plc:
                    try: plc.close()
                    except Exception: pass
                for conn in io_connections.values():
                    try: conn.close()
                    except Exception: pass
                io_connections.clear()
                plc=None; sleep_i(RECONNECT_DELAY)
        return 0
    finally:
        if plc:
            try: plc.close()
            except Exception: pass
        for conn in io_connections.values():
            try: conn.close()
            except Exception: pass
        for s in SENSORS:
            try: c.publish(topics(s)[3],"offline",qos=1,retain=True)
            except Exception: pass
        for light in LIGHTS:
            try: c.publish(light_topics(light)[3],"offline",qos=1,retain=True)
            except Exception: pass
        c.loop_stop(); c.disconnect()

if __name__=='__main__': sys.exit(main())
