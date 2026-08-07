from __future__ import annotations
import json, logging, os, signal, sys, threading, time
from typing import Any
import paho.mqtt.client as mqtt
import pyads

VERSION = "1.2.0"
PLC_IP = os.environ["PLC_IP"]
PLC_AMS_NET_ID = os.environ["PLC_AMS_NET_ID"]
LOCAL_AMS_NET_ID = os.environ["LOCAL_AMS_NET_ID"]
PLC_ADS_PORT = int(os.environ["PLC_ADS_PORT"])
POLL_INTERVAL = int(os.environ["POLL_INTERVAL"])
RECONNECT_DELAY = int(os.environ["RECONNECT_DELAY"])
PUBLISH_HEARTBEAT = int(os.environ["PUBLISH_HEARTBEAT"])
ADD_LOCAL_ROUTE = os.environ.get("ADD_LOCAL_ROUTE", "true").lower() == "true"
SENSORS_JSON = os.environ["SENSORS_JSON"]
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

stop_requested = False
mqtt_connected = threading.Event()
route_configured = False

def stop_handler(_s:int,_f:Any)->None:
    global stop_requested; stop_requested=True
signal.signal(signal.SIGTERM, stop_handler); signal.signal(signal.SIGINT, stop_handler)

def on_connect(client, userdata, flags, reason_code, properties=None):
    if not bool(getattr(reason_code, "is_failure", False)):
        LOGGER.info("MQTT connected to %s:%s (reason=%s)", MQTT_HOST, MQTT_PORT, reason_code); mqtt_connected.set()
    else: LOGGER.error("MQTT connection failed: %s", reason_code)

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
    mqtt_connected.clear()
    if not stop_requested: LOGGER.warning("MQTT disconnected: %s", reason_code)

def mqtt_client():
    c=mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id="beckhoff_ads_gateway")
    c.on_connect=on_connect; c.on_disconnect=on_disconnect
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
    configure_route_once()
    plc=None; last={}; last_pub={}; reconnects=0; scanned=False
    try:
        while not stop_requested:
            try:
                if plc is None or not plc.is_open:
                    plc=open_plc(); scanned=False
                if not scanned:
                    scan_hvac(plc); scanned=True
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
                sleep_i(POLL_INTERVAL)
            except Exception as err:
                reconnects+=1; LOGGER.exception("ADS connection failed: %s; reconnect #%d in %ds",err,reconnects,RECONNECT_DELAY)
                if plc:
                    try: plc.close()
                    except Exception: pass
                plc=None; sleep_i(RECONNECT_DELAY)
        return 0
    finally:
        if plc:
            try: plc.close()
            except Exception: pass
        for s in SENSORS:
            try: c.publish(topics(s)[3],"offline",qos=1,retain=True)
            except Exception: pass
        c.loop_stop(); c.disconnect()

if __name__=='__main__': sys.exit(main())
