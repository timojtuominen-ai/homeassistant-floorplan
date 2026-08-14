#!/usr/bin/env python3
import json, logging, os, socket, threading, time
from pathlib import Path
import paho.mqtt.client as mqtt
import pyads

OPT=json.loads(Path("/data/options.json").read_text())
ENT=json.loads(Path("/app/entities.json").read_text())
PLC_IP=OPT["plc_ip"]; PLC_AMS=OPT["plc_ams_net_id"]; LOCAL_AMS=OPT["local_ams_net_id"]
ADS_PORT=int(OPT.get("plc_ads_port",851)); POLL=float(OPT.get("poll_interval",1.0))
RECONNECT=int(OPT.get("reconnect_delay",5)); PULSE=int(OPT.get("command_pulse_ms",200))/1000.0
DISCOVERY=bool(OPT.get("publish_discovery",True))
MQTT_HOST=os.getenv("MQTT_HOST","core-mosquitto"); MQTT_PORT=int(os.getenv("MQTT_PORT","1883"))
MQTT_USER=os.getenv("MQTT_USER",""); MQTT_PASSWORD=os.getenv("MQTT_PASSWORD","")
logging.basicConfig(level=getattr(logging,OPT.get("log_level","INFO")),format="%(asctime)s %(levelname)s %(message)s")
log=logging.getLogger("beckhoff_cx9240_gateway")
plc=None; mqttc=None; ads_lock=threading.Lock(); symbol_cache={}; command_map={}
LEGACY_DEVICE_ID="beckhoff_cx5000_ads"
ROOMS={"olohuone":["oh_kulku_spotit","oh_pihan_puolen_ruokapoyta","oh_terassin_puolen_valot","oh_keskivalo","oh_epasuora_pihanseina","oh_epasuora_paatyseina","oh_epasuora_terassinseina","oh_pihan_puolen_kohdevalot"],"keittio":["keittio_valitila_valo","keittio_valo","ruokatila_valo","keittio_ruokatila_kaytava","keittio_kaappien_paalla_valo"],"lt_mh":["lt_vaatehuonevalot","lt_spotit","lt_epasuora_valo"],"allun_mh":["allun_spotit","allun_kattovalo"],"emman_mh":["emman_spotit","emman_kattovalo"],"wc_lt":["wc_lt_kattovalo","wc_lt_allasvalo"],"wc_lasten":["wc_lasten_kattovalo","wc_lasten_allasvalo"],"autotalli":["autotalli_valot"],"tuulikaappi":["tuulikaappi_valot"],"khh":["khh_kaytava_valot","khh_ikkuna_valot"],"kellari":["kellari_spotit","kellari_isot_valot"],"tyohuone":["tyohuone_valo"],"eteinen":["eteinen_valot"],"suihku":["suihkun_valo"],"wc_alakerta":["wc_alakerta_kattovalo"],"kylmakellari":["kylmakellari_valo"],"kellarin_varasto":["kellarin_varasto_valo"],"tekninen_tila":["tekninen_tila_valo"],"sauna":["saunan_valo"]}
ROOM_NAMES={"olohuone":"Olohuone valot päällä","keittio":"Keittiö valot päällä","lt_mh":"L&T MH valot päällä","allun_mh":"Allun MH valot päällä","emman_mh":"Emman MH valot päällä","wc_lt":"WC L&T valot päällä","wc_lasten":"WC lasten valot päällä","autotalli":"Autotalli valot päällä","tuulikaappi":"Tuulikaappi valot päällä","khh":"KHH valot päällä","kellari":"Kellari valot päällä","tyohuone":"Työhuone valot päällä","eteinen":"Eteinen valot päällä","suihku":"Suihku valot päällä","wc_alakerta":"Alakerran WC valot päällä","kylmakellari":"Kylmäkellari valot päällä","kellarin_varasto":"Kellarin varasto valot päällä","tekninen_tila":"Tekninen tila valot päällä","sauna":"Sauna valot päällä"}

def device():
    return {"identifiers":[LEGACY_DEVICE_ID],"name":"Beckhoff CX9240","manufacturer":"Beckhoff","model":"CX9240 / TwinCAT 3","sw_version":"Kotiautomaatio_TC3 v0.30"}
def resolve(name):
    if name not in symbol_cache:
        symbol_cache[name]=plc.get_symbol(name); log.info("ADS symbol resolved: %s",name)
    return symbol_cache[name]
def read(name):
    with ads_lock: return resolve(name).read()
def write(name,val):
    with ads_lock: resolve(name).write(val)
def pulse(name):
    write(name,True); time.sleep(PULSE); write(name,False)
def legacy_topics(domain,oid):
    if domain=="light": return (f"homeassistant/light/beckhoff_ads/{oid}/config",f"beckhoff_ads/light/{oid}/state",f"beckhoff_ads/light/{oid}/set",f"beckhoff_ads/light/{oid}/availability")
    if domain=="sensor": return (f"homeassistant/sensor/beckhoff_ads/{oid}/config",f"beckhoff_ads/{oid}/state",None,f"beckhoff_ads/{oid}/availability")
    if domain=="binary_sensor": return (f"homeassistant/binary_sensor/beckhoff_ads/{oid}/config",f"beckhoff_ads/binary/{oid}/state",None,f"beckhoff_ads/binary/{oid}/availability")
    raise ValueError(domain)
def publish_legacy_config(domain,e):
    oid=e["legacy_object_id"]; disc,state,cmd,avail=legacy_topics(domain,oid)
    if domain=="light":
        cfg={"name":e["name"],"unique_id":f"beckhoff_ads_light_{oid}","default_entity_id":f"light.{oid}","state_topic":state,"command_topic":cmd,"availability_topic":avail,"payload_available":"online","payload_not_available":"offline","payload_on":"ON","payload_off":"OFF","state_on":"ON","state_off":"OFF","optimistic":False,"icon":"mdi:lightbulb","device":device()}; command_map[cmd]={"on":e["on_symbol"],"off":e["off_symbol"]}
    elif domain=="sensor":
        cfg={"name":e["name"],"unique_id":f"beckhoff_ads_{oid}","default_entity_id":f"sensor.{oid}","state_topic":state,"availability_topic":avail,"payload_available":"online","payload_not_available":"offline","unit_of_measurement":e.get("unit","°C"),"device_class":e.get("device_class","temperature"),"state_class":"measurement","device":device()}
    else:
        cfg={"name":e["name"],"unique_id":f"beckhoff_ads_binary_{oid}","default_entity_id":f"binary_sensor.{oid}","state_topic":state,"availability_topic":avail,"payload_available":"online","payload_not_available":"offline","payload_on":"ON","payload_off":"OFF","device":device()}
        if e.get("device_class"): cfg["device_class"]=e["device_class"]
    mqttc.publish(disc,json.dumps(cfg,ensure_ascii=False),retain=True); mqttc.publish(avail,"online",retain=True)
def publish_switch_config(e):
    oid=e["legacy_object_id"]
    if oid=="liesituuletin_30min": disc=f"homeassistant/switch/beckhoff_ads/{oid}/config"; state=f"beckhoff_ads/timed/{oid}/state"; cmd=f"beckhoff_ads/timed/{oid}/set"; avail=f"beckhoff_ads/timed/{oid}/availability"; uid=f"beckhoff_ads_timed_{oid}"
    else: disc=f"homeassistant/switch/beckhoff_cx9240/{oid}/config"; state=f"beckhoff_cx9240/switch/{oid}/state"; cmd=f"beckhoff_cx9240/switch/{oid}/set"; avail="beckhoff_cx9240/availability"; uid=f"beckhoff_cx9240_{oid}"
    cfg={"name":e["name"],"unique_id":uid,"default_entity_id":f"switch.{oid}","state_topic":state,"command_topic":cmd,"availability_topic":avail,"payload_available":"online","payload_not_available":"offline","payload_on":"ON","payload_off":"OFF","state_on":"ON","state_off":"OFF","optimistic":False,"device":device()}
    mqttc.publish(disc,json.dumps(cfg,ensure_ascii=False),retain=True); mqttc.publish(avail,"online",retain=True); command_map[cmd]={"on":e["on_symbol"],"off":e["off_symbol"]}
def publish_room_configs():
    for rid,lids in ROOMS.items():
        disc=f"homeassistant/sensor/beckhoff_ads/{rid}_valot_paalla/config"; state=f"beckhoff_ads/room/{rid}/lights_on/state"; avail=f"beckhoff_ads/room/{rid}/lights_on/availability"
        cfg={"name":ROOM_NAMES[rid],"unique_id":f"beckhoff_ads_room_{rid}_lights_on","default_entity_id":f"sensor.{rid}_valot_paalla","state_topic":state,"availability_topic":avail,"payload_available":"online","payload_not_available":"offline","unit_of_measurement":f"/ {len(lids)}","icon":"mdi:lightbulb-group","device":device()}
        mqttc.publish(disc,json.dumps(cfg,ensure_ascii=False),retain=True); mqttc.publish(avail,"online",retain=True)
def setup_discovery():
    if not DISCOVERY:return
    command_map.clear()
    for e in ENT["lights"]: publish_legacy_config("light",e)
    for e in ENT["sensors"]: publish_legacy_config("sensor",e)
    for e in ENT["binary_sensors"]: publish_legacy_config("binary_sensor",e)
    for e in ENT["switches"]: publish_switch_config(e)
    publish_room_configs(); mqttc.publish("beckhoff_cx9240/availability","online",retain=True)
    for topic in command_map: mqttc.subscribe(topic)
    log.info("MQTT legacy-compatible discovery published: %d lights, %d sensors, %d binary sensors, %d switches, %d rooms",len(ENT["lights"]),len(ENT["sensors"]),len(ENT["binary_sensors"]),len(ENT["switches"]),len(ROOMS))
def on_connect(client,userdata,flags,reason_code,properties): log.info("MQTT connected: %s",reason_code); setup_discovery()
def on_message(client,userdata,msg):
    c=command_map.get(msg.topic)
    if not c:return
    val=msg.payload.decode().strip().upper()
    if val not in ("ON","OFF"):return
    sym=c["on"] if val=="ON" else c["off"]; threading.Thread(target=pulse,args=(sym,),daemon=True).start(); log.info("Command %s -> %s (%s)",msg.topic,val,sym)
def prepare_ads():
    pyads.open_port()
    try: pyads.set_local_address(LOCAL_AMS)
    finally: pyads.close_port()
    with socket.create_connection((PLC_IP,48898),timeout=3): pass
def connect_ads():
    global plc
    prepare_ads(); p=pyads.Connection(PLC_AMS,ADS_PORT,PLC_IP); p.open(); plc=p; symbol_cache.clear(); online=read("GVL_HA.xOnline"); log.info("ADS connected to %s / %s port %s, xOnline=%s",PLC_IP,PLC_AMS,ADS_PORT,online)
def pub(topic,val): mqttc.publish(topic,val,retain=True)
def poll_once():
    light_states={}
    for e in ENT["lights"]:
        v=bool(read(e["state_symbol"])); light_states[e["legacy_object_id"]]=v; _,state,_,avail=legacy_topics("light",e["legacy_object_id"]); pub(state,"ON" if v else "OFF"); pub(avail,"online")
    for e in ENT["sensors"]:
        v=read(e["symbol"]); _,state,_,avail=legacy_topics("sensor",e["legacy_object_id"]); pub(state,f"{float(v):.1f}"); pub(avail,"online")
    for e in ENT["binary_sensors"]:
        v=bool(read(e["symbol"])); v=(not v) if e.get("invert") else v; _,state,_,avail=legacy_topics("binary_sensor",e["legacy_object_id"]); pub(state,"ON" if v else "OFF"); pub(avail,"online")
    for e in ENT["switches"]:
        oid=e["legacy_object_id"]; v=bool(read(e["state_symbol"])); state=f"beckhoff_ads/timed/{oid}/state" if oid=="liesituuletin_30min" else f"beckhoff_cx9240/switch/{oid}/state"; pub(state,"ON" if v else "OFF")
    for rid,lids in ROOMS.items():
        count=sum(1 for lid in lids if light_states.get(lid,False)); pub(f"beckhoff_ads/room/{rid}/lights_on/state",str(count)); pub(f"beckhoff_ads/room/{rid}/lights_on/availability","online")
    pub("beckhoff_cx9240/availability","online")
def main():
    global mqttc,plc
    log.info("Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.2 legacy-HA compatibility")
    mqttc=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id="beckhoff_cx9240_gateway")
    if MQTT_USER:mqttc.username_pw_set(MQTT_USER,MQTT_PASSWORD)
    mqttc.will_set("beckhoff_cx9240/availability","offline",retain=True); mqttc.on_connect=on_connect; mqttc.on_message=on_message; mqttc.connect(MQTT_HOST,MQTT_PORT,60); mqttc.loop_start()
    while True:
        try:
            if plc is None or not plc.is_open: connect_ads()
            poll_once(); time.sleep(POLL)
        except Exception as exc:
            log.warning("ADS/poll error: %s",exc)
            try:
                if plc: plc.close()
            except Exception: pass
            plc=None; symbol_cache.clear(); time.sleep(RECONNECT)
if __name__=="__main__": main()
