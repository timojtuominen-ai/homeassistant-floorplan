from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.14: group-off buttons and persistent cleaning-light mode switches.
EXTRA_SWITCHES_V114 = [
    {
        "legacy_object_id": "siivousvalot_alakerta",
        "name": "Siivousvalot alakerta",
        "state_symbol": "GVL_HA.xCleaningLightsDownstairsActive",
        "on_symbol": "GVL_HA.xCmdCleaningLightsDownstairsOn",
        "off_symbol": "GVL_HA.xCmdCleaningLightsDownstairsOff",
    },
    {
        "legacy_object_id": "siivousvalot_ylakerta",
        "name": "Siivousvalot yläkerta",
        "state_symbol": "GVL_HA.xCleaningLightsUpstairsActive",
        "on_symbol": "GVL_HA.xCmdCleaningLightsUpstairsOn",
        "off_symbol": "GVL_HA.xCmdCleaningLightsUpstairsOff",
    },
]
for _e in EXTRA_SWITCHES_V114:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["switches"]):
        ENT["switches"].append(_e)

EXTRA_BUTTONS_V114 = [
    {"object_id":"kaikki_valot_pois","name":"Kaikki valot pois","command_symbol":"GVL_HA.xCmdAllLightsOff","icon":"mdi:lightbulb-group-off"},
    {"object_id":"alakerran_valot_pois","name":"Alakerran valot pois","command_symbol":"GVL_HA.xCmdDownstairsLightsOff","icon":"mdi:home-floor-0"},
    {"object_id":"ylakerran_valot_pois","name":"Yläkerran valot pois","command_symbol":"GVL_HA.xCmdUpstairsLightsOff","icon":"mdi:home-floor-1"},
    {"object_id":"tallin_liiterin_valot_pois","name":"Tallin/liiterin valot pois","command_symbol":"GVL_HA.xCmdGarageWoodshedLightsOff","icon":"mdi:garage-variant"},
]

def publish_button_config(e):
    oid=e["object_id"]
    disc=f"homeassistant/button/beckhoff_cx9240/{oid}/config"
    cmd=f"beckhoff_cx9240/button/{oid}/press"
    cfg={"name":e["name"],"unique_id":f"beckhoff_cx9240_{oid}","default_entity_id":f"button.{oid}","command_topic":cmd,"availability_topic":"beckhoff_cx9240/availability","payload_available":"online","payload_not_available":"offline","payload_press":"PRESS","icon":e.get("icon","mdi:gesture-tap-button"),"device":device()}
    mqttc.publish(disc,json.dumps(cfg,ensure_ascii=False),retain=True)
    command_map[cmd]={"kind":"button","symbol":e["command_symbol"]}
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.14 discovery insertion point was not found")
s = s.replace(marker, insert + marker, 1)

switch_loop = '    for e in ENT["switches"]: publish_switch_config(e)\n'
if switch_loop not in s:
    raise RuntimeError("v1.0.14 switch discovery loop was not found")
s = s.replace(switch_loop, switch_loop + '    for e in EXTRA_BUTTONS_V114: publish_button_config(e)\n', 1)

message_marker = '''    val=raw.upper()
    if val not in ("ON","OFF"):return'''
message_replacement = '''    if c.get("kind")=="button":
        if raw.upper()!="PRESS":return
        sym=c["symbol"]
        threading.Thread(target=pulse,args=(sym,),daemon=True).start()
        log.info("Button command %s -> %s",msg.topic,sym)
        return
    val=raw.upper()
    if val not in ("ON","OFF"):return'''
if message_marker not in s:
    raise RuntimeError("v1.0.14 command-handler insertion point was not found")
s = s.replace(message_marker, message_replacement, 1)

s = s.replace('"sw_version":"Kotiautomaatio_TC3 v0.34.0"','"sw_version":"Kotiautomaatio_TC3 v0.34.1"',1)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.13 outbuilding lights and garage temperature",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.14 lighting groups and cleaning modes",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.14")
