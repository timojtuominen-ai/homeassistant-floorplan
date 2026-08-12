#!/usr/bin/env python3
import json, logging, os, socket, threading, time
from pathlib import Path

import paho.mqtt.client as mqtt
import pyads

OPT = json.loads(Path("/data/options.json").read_text())
ENT = json.loads(Path("/app/entities.json").read_text())

PLC_IP = OPT["plc_ip"]
PLC_AMS = OPT["plc_ams_net_id"]
LOCAL_AMS = OPT["local_ams_net_id"]
ADS_PORT = int(OPT.get("plc_ads_port", 851))
POLL = float(OPT.get("poll_interval", 1.0))
RECONNECT = int(OPT.get("reconnect_delay", 5))
PULSE = int(OPT.get("command_pulse_ms", 200)) / 1000.0
TEST = bool(OPT.get("test_mode", True))
DISCOVERY = bool(OPT.get("publish_discovery", True))

MQTT_HOST = os.getenv("MQTT_HOST","core-mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT","1883"))
MQTT_USER = os.getenv("MQTT_USER","")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD","")

logging.basicConfig(level=getattr(logging, OPT.get("log_level","INFO")),
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("beckhoff_tc3_gateway")

PREFIX = "beckhoff_tc3_test" if TEST else "beckhoff_cx5000"
DEVICE_NAME = "Beckhoff CX9240 TEST" if TEST else "Beckhoff CX9240"
DEVICE_ID = "beckhoff_cx9240_test" if TEST else "beckhoff_cx5000"

ads_lock = threading.Lock()
plc = None
mqttc = None
command_map = {}

def obj_id(legacy):
    return ("tc3_test_" + legacy) if TEST else legacy

def topic_base(domain, legacy):
    return f"{PREFIX}/{domain}/{obj_id(legacy)}"

def discovery_topic(domain, legacy):
    return f"homeassistant/{domain}/{DEVICE_ID}/{obj_id(legacy)}/config"

def device():
    return {"identifiers":[DEVICE_ID],"name":DEVICE_NAME,
            "manufacturer":"Beckhoff","model":"CX9240 / TwinCAT 3",
            "sw_version":"Kotiautomaatio_TC3 v0.22"}

def read_symbol(symbol, typ):
    with ads_lock:
        return plc.read_by_name(symbol, typ)

def write_symbol(symbol, value, typ):
    with ads_lock:
        plc.write_by_name(symbol, value, typ)

def pulse_symbol(symbol):
    write_symbol(symbol, True, pyads.PLCTYPE_BOOL)
    time.sleep(PULSE)
    write_symbol(symbol, False, pyads.PLCTYPE_BOOL)

def publish_config(domain, legacy, name, state_topic, extra=None, command_topic=None):
    cfg = {
        "name": name,
        "object_id": obj_id(legacy),
        "unique_id": f"{DEVICE_ID}_{obj_id(legacy)}",
        "state_topic": state_topic,
        "availability_topic": f"{PREFIX}/availability",
        "payload_available":"online","payload_not_available":"offline",
        "device": device(),
    }
    if command_topic:
        cfg["command_topic"] = command_topic
        cfg["payload_on"] = "ON"; cfg["payload_off"] = "OFF"
    if extra: cfg.update(extra)
    mqttc.publish(discovery_topic(domain, legacy), json.dumps(cfg, ensure_ascii=False), retain=True)

def setup_discovery():
    if not DISCOVERY: return
    for e in ENT["lights"]:
        legacy=e["legacy_object_id"]; base=topic_base("light",legacy)
        publish_config("light",legacy,e["name"],base+"/state",command_topic=base+"/set")
        command_map[base+"/set"]={"kind":"pulse_switch","on":e["on_symbol"],"off":e["off_symbol"]}
    for e in ENT["sensors"]:
        legacy=e["legacy_object_id"]; base=topic_base("sensor",legacy)
        extra={"state_class":"measurement"}
        if e.get("unit"): extra["unit_of_measurement"]=e["unit"]
        if e.get("device_class")=="temperature": extra["device_class"]="temperature"
        publish_config("sensor",legacy,e["name"],base+"/state",extra=extra)
    for e in ENT["binary_sensors"]:
        legacy=e["legacy_object_id"]; base=topic_base("binary_sensor",legacy)
        extra={"payload_on":"ON","payload_off":"OFF"}
        if e.get("device_class"): extra["device_class"]=e["device_class"]
        publish_config("binary_sensor",legacy,e["name"],base+"/state",extra=extra)
    for e in ENT["switches"]:
        legacy=e["legacy_object_id"]; base=topic_base("switch",legacy)
        publish_config("switch",legacy,e["name"],base+"/state",command_topic=base+"/set")
        command_map[base+"/set"]={"kind":"pulse_switch" if e.get("pulse") else "direct_switch",
                                  "on":e["on_symbol"],"off":e["off_symbol"]}
    base=topic_base("binary_sensor","gateway_online")
    publish_config("binary_sensor","gateway_online","TC3 Gateway online",base+"/state",
                   extra={"payload_on":"ON","payload_off":"OFF","device_class":"connectivity"})
    mqttc.publish(f"{PREFIX}/availability","online",retain=True)
    log.info("MQTT discovery published: %d lights, %d sensors, %d binary sensors, %d switches",
             len(ENT["lights"]),len(ENT["sensors"]),len(ENT["binary_sensors"]),len(ENT["switches"]))

def on_connect(client, userdata, flags, reason_code, properties):
    log.info("MQTT connected: %s", reason_code)
    setup_discovery()
    for t in command_map:
        client.subscribe(t)

def on_message(client, userdata, msg):
    try:
        cmd=command_map.get(msg.topic)
        if not cmd: return
        val=msg.payload.decode().strip().upper()
        if val not in ("ON","OFF"): return
        if cmd["kind"]=="pulse_switch":
            sym=cmd["on"] if val=="ON" else cmd["off"]
            threading.Thread(target=pulse_symbol,args=(sym,),daemon=True).start()
        else:
            sym=cmd["on"] if val=="ON" else cmd["off"]
            write_symbol(sym, val=="ON", pyads.PLCTYPE_BOOL)
        log.info("Command %s -> %s", msg.topic, val)
    except Exception:
        log.exception("MQTT command failed")

def prepare_linux_ads_client():
    """Set the Linux client's AMS Net ID. Connection.open() creates the client-side route."""
    log.info("ADS client: opening local ADS port to set AMS Net ID")
    pyads.open_port()
    try:
        log.info("ADS client: setting local AMS Net ID to %s", LOCAL_AMS)
        pyads.set_local_address(LOCAL_AMS)
    finally:
        pyads.close_port()
    log.info("ADS client: local AMS Net ID configured")

def probe_ads_tcp():
    """Give an immediate, clear network diagnostic before pyads opens the ADS route."""
    log.info("ADS network probe: testing %s:48898", PLC_IP)
    with socket.create_connection((PLC_IP, 48898), timeout=3.0):
        pass
    log.info("ADS network probe: TCP 48898 reachable")

def connect_ads():
    global plc
    log.info("ADS connect: preparing Linux client")
    prepare_linux_ads_client()
    probe_ads_tcp()
    log.info("ADS connect: opening PLC connection to %s / %s port %s (client route auto-created by pyads)", PLC_IP, PLC_AMS, ADS_PORT)
    p=pyads.Connection(PLC_AMS, ADS_PORT, PLC_IP)
    p.open()
    log.info("ADS connect: transport opened, reading GVL_HA.xOnline")
    online=p.read_by_name("GVL_HA.xOnline", pyads.PLCTYPE_BOOL)
    log.info("ADS connected to %s / %s port %s, GVL_HA.xOnline=%s", PLC_IP,PLC_AMS,ADS_PORT,online)
    plc=p

def pub_state(domain, legacy, value):
    mqttc.publish(topic_base(domain,legacy)+"/state", value, retain=True)

def poll_once():
    for e in ENT["lights"]:
        v=read_symbol(e["state_symbol"],pyads.PLCTYPE_BOOL)
        pub_state("light",e["legacy_object_id"],"ON" if v else "OFF")
    for e in ENT["sensors"]:
        v=read_symbol(e["symbol"],pyads.PLCTYPE_REAL)
        pub_state("sensor",e["legacy_object_id"],f"{float(v):.1f}")
    for e in ENT["binary_sensors"]:
        v=bool(read_symbol(e["symbol"],pyads.PLCTYPE_BOOL))
        if e.get("invert"): v=not v
        pub_state("binary_sensor",e["legacy_object_id"],"ON" if v else "OFF")
    for e in ENT["switches"]:
        v=bool(read_symbol(e["state_symbol"],pyads.PLCTYPE_BOOL))
        pub_state("switch",e["legacy_object_id"],"ON" if v else "OFF")
    pub_state("binary_sensor","gateway_online","ON")
    mqttc.publish(f"{PREFIX}/availability","online",retain=True)

def main():
    global mqttc, plc
    log.info("Starting Beckhoff TC3 Gateway TEST v0.1.2")
    log.info("Mode=%s, PLC=%s AMS=%s ADS=%s LocalAMS=%s", "TEST" if TEST else "PRODUCTION",PLC_IP,PLC_AMS,ADS_PORT,LOCAL_AMS)
    mqttc=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"{DEVICE_ID}_gateway")
    if MQTT_USER: mqttc.username_pw_set(MQTT_USER,MQTT_PASSWORD)
    mqttc.will_set(f"{PREFIX}/availability","offline",retain=True)
    mqttc.on_connect=on_connect
    mqttc.on_message=on_message
    mqttc.connect(MQTT_HOST,MQTT_PORT,60)
    mqttc.loop_start()

    while True:
        try:
            if plc is None or not plc.is_open:
                connect_ads()
            poll_once()
            time.sleep(POLL)
        except Exception as exc:
            log.warning("ADS/poll error: %s", exc)
            try:
                pub_state("binary_sensor","gateway_online","OFF")
                mqttc.publish(f"{PREFIX}/availability","offline",retain=True)
            except Exception: pass
            try:
                if plc: plc.close()
            except Exception: pass
            plc=None
            time.sleep(RECONNECT)

if __name__=="__main__":
    main()
