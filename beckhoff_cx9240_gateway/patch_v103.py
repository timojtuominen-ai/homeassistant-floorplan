from pathlib import Path

p = Path('/app/main.py')
s = p.read_text(encoding='utf-8')

# v1.0.3 targets PLC v0.31 and adds commissioning statuses + writable number entities.
s = s.replace('"sw_version":"Kotiautomaatio_TC3 v0.30"', '"sw_version":"Kotiautomaatio_TC3 v0.31"')
s = s.replace('Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.2 legacy-HA compatibility', 'Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.3 commissioning + heating controls')

insert = r'''

# v1.0.3 commissioning status entities. Existing IDs are left untouched.
EXTRA_BINARY = [
    {"legacy_object_id":"burglary_exit_delay","name":"Murtohälytys - poistumisviive 60 s","symbol":"GVL_HA.xBurglaryExitDelayActive","device_class":None,"invert":False},
    {"legacy_object_id":"burglary_entry_delay","name":"Murtohälytys - sisääntuloviive 45 s","symbol":"GVL_HA.xBurglaryEntryDelayActive","device_class":None,"invert":False},
    {"legacy_object_id":"burglary_arming_blocked","name":"Murtohälytys - kytkentä estetty","symbol":"GVL_HA.xBurglaryArmingBlocked","device_class":"problem","invert":False},
    {"legacy_object_id":"burglary_arming_ready","name":"Murtohälytys - kaikki valvontapiirit normaalit","symbol":"GVL_HA.xBurglaryArmingReady","device_class":None,"invert":False},
]
for _e in EXTRA_BINARY:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)

# Writable Home Assistant number entities. PLC owns the control logic; HA changes only parameters.
NUMBERS = [
    # Six actual room-heating setpoints (workroom intentionally omitted: no thermostat/actuator).
    {"id":"emman_huone_setpoint","name":"Emman huone lämmitys asetusarvo","symbol":"GVL_HA.rSetpoint_02_Emman_huone_lampotila","min":5.0,"max":30.0,"step":0.5,"unit":"°C"},
    {"id":"allun_huone_setpoint","name":"Allun huone lämmitys asetusarvo","symbol":"GVL_HA.rSetpoint_03_Allun_huone_lampotila","min":5.0,"max":30.0,"step":0.5,"unit":"°C"},
    {"id":"olohuone_setpoint","name":"Olohuone lämmitys asetusarvo","symbol":"GVL_HA.rSetpoint_04_Olohuone_lampotila","min":5.0,"max":30.0,"step":0.5,"unit":"°C"},
    {"id":"lt_mh_setpoint","name":"Makuuhuone L&T lämmitys asetusarvo","symbol":"GVL_HA.rSetpoint_05_Makuuhuone_L_ja_T_lampotila","min":5.0,"max":30.0,"step":0.5,"unit":"°C"},
    {"id":"keittio_setpoint","name":"Keittiö / ruokatila lämmitys asetusarvo","symbol":"GVL_HA.rSetpoint_07_Ruokatila_lampotila","min":5.0,"max":30.0,"step":0.5,"unit":"°C"},
    {"id":"kellari_setpoint","name":"Kellari lämmitys asetusarvo","symbol":"GVL_HA.rSetpoint_10_Kellari_lampotila","min":5.0,"max":30.0,"step":0.5,"unit":"°C"},

    # Offset adjustment for every temperature measurement. Valoisuus (channel 14) is deliberately excluded.
    {"id":"talli_temperature_offset","name":"Talli lämpötila offset","symbol":"GVL_HA.rOffset_01_Tallin_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"emma_temperature_offset","name":"Emman huone lämpötila offset","symbol":"GVL_HA.rOffset_02_Emman_huone_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"allu_temperature_offset","name":"Allun huone lämpötila offset","symbol":"GVL_HA.rOffset_03_Allun_huone_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"olohuone_temperature_offset","name":"Olohuone lämpötila offset","symbol":"GVL_HA.rOffset_04_Olohuone_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"lt_mh_temperature_offset","name":"Makuuhuone L&T lämpötila offset","symbol":"GVL_HA.rOffset_05_Makuuhuone_L_ja_T_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"tyohuone_temperature_offset","name":"Työhuone lämpötila offset","symbol":"GVL_HA.rOffset_06_Tyohuone_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"keittio_temperature_offset","name":"Keittiö / ruokatila lämpötila offset","symbol":"GVL_HA.rOffset_07_Ruokatila_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"sauna_temperature_offset","name":"Sauna lämpötila offset","symbol":"GVL_HA.rOffset_08_Sauna","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"kylmakellari_temperature_offset","name":"Kylmäkellari lämpötila offset","symbol":"GVL_HA.rOffset_09_Kylmakellari","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"kellari_temperature_offset","name":"Kellari lämpötila offset","symbol":"GVL_HA.rOffset_10_Kellari_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"lattialammitys_meno_offset","name":"Lattialämmitys meno lämpötila offset","symbol":"GVL_HA.rOffset_11_Lattialammitys_meno_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"lattialammitys_paluu_offset","name":"Lattialämmitys paluu lämpötila offset","symbol":"GVL_HA.rOffset_12_Lattialammitys_paluu_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"ulkolampotila_offset","name":"Ulkolämpötila offset","symbol":"GVL_HA.rOffset_13_ulkolampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"palju_paluu_temperature_offset","name":"Palju paluu lämpötila offset","symbol":"GVL_HA.rOffset_15_Palju_veden_paluu_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
    {"id":"palju_poisto_temperature_offset","name":"Palju poisto lämpötila offset","symbol":"GVL_HA.rOffset_16_Palju_veden_poisto_lampotila","min":-15.0,"max":15.0,"step":0.1,"unit":"°C"},
]

def number_topics(e):
    oid=e["id"]
    return (f"homeassistant/number/beckhoff_cx9240/{oid}/config", f"beckhoff_cx9240/number/{oid}/state", f"beckhoff_cx9240/number/{oid}/set")

def publish_number_config(e):
    disc,state,cmd=number_topics(e)
    cfg={"name":e["name"],"unique_id":f"beckhoff_cx9240_number_{e['id']}","default_entity_id":f"number.{e['id']}","state_topic":state,"command_topic":cmd,"availability_topic":"beckhoff_cx9240/availability","payload_available":"online","payload_not_available":"offline","min":e["min"],"max":e["max"],"step":e["step"],"mode":"box","unit_of_measurement":e.get("unit"),"device":device()}
    mqttc.publish(disc,json.dumps(cfg,ensure_ascii=False),retain=True)
    command_map[cmd]={"kind":"number","symbol":e["symbol"],"min":e["min"],"max":e["max"]}
'''

s = s.replace('\ndef setup_discovery():', insert + '\n\ndef setup_discovery():')
s = s.replace('    for e in ENT["switches"]: publish_switch_config(e)\n    publish_room_configs();', '    for e in ENT["switches"]: publish_switch_config(e)\n    for e in NUMBERS: publish_number_config(e)\n    publish_room_configs();')
s = s.replace('log.info("MQTT legacy-compatible discovery published: %d lights, %d sensors, %d binary sensors, %d switches, %d rooms",len(ENT["lights"]),len(ENT["sensors"]),len(ENT["binary_sensors"]),len(ENT["switches"]),len(ROOMS))', 'log.info("MQTT legacy-compatible discovery published: %d lights, %d sensors, %d binary sensors, %d switches, %d rooms, %d numbers",len(ENT["lights"]),len(ENT["sensors"]),len(ENT["binary_sensors"]),len(ENT["switches"]),len(ROOMS),len(NUMBERS))')

old_msg = '''def on_message(client,userdata,msg):
    c=command_map.get(msg.topic)
    if not c:return
    val=msg.payload.decode().strip().upper()
    if val not in ("ON","OFF"):return
    sym=c["on"] if val=="ON" else c["off"]; threading.Thread(target=pulse,args=(sym,),daemon=True).start(); log.info("Command %s -> %s (%s)",msg.topic,val,sym)'''
new_msg = '''def on_message(client,userdata,msg):
    c=command_map.get(msg.topic)
    if not c:return
    raw=msg.payload.decode().strip()
    if c.get("kind")=="number":
        try:
            val=float(raw)
            val=max(float(c["min"]),min(float(c["max"]),val))
            write(c["symbol"],val)
            log.info("Number command %s -> %.3f (%s)",msg.topic,val,c["symbol"])
        except Exception:
            log.exception("Invalid number command %s payload=%r",msg.topic,raw)
        return
    val=raw.upper()
    if val not in ("ON","OFF"):return
    sym=c["on"] if val=="ON" else c["off"]; threading.Thread(target=pulse,args=(sym,),daemon=True).start(); log.info("Command %s -> %s (%s)",msg.topic,val,sym)'''
if old_msg not in s:
    raise RuntimeError('on_message patch target not found')
s=s.replace(old_msg,new_msg)

s=s.replace('    for rid,lids in ROOMS.items():\n        count=sum(1 for lid in lids if light_states.get(lid,False)); pub(f"beckhoff_ads/room/{rid}/lights_on/state",str(count)); pub(f"beckhoff_ads/room/{rid}/lights_on/availability","online")\n    pub("beckhoff_cx9240/availability","online")', '    for rid,lids in ROOMS.items():\n        count=sum(1 for lid in lids if light_states.get(lid,False)); pub(f"beckhoff_ads/room/{rid}/lights_on/state",str(count)); pub(f"beckhoff_ads/room/{rid}/lights_on/availability","online")\n    for e in NUMBERS:\n        _,state,_=number_topics(e); pub(state,f"{float(read(e[\"symbol\"])):.2f}")\n    pub("beckhoff_cx9240/availability","online")')

p.write_text(s,encoding='utf-8')
print('patched gateway main.py for v1.0.3')
