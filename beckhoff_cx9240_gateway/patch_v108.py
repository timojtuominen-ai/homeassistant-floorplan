from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.8: hot-tub temperatures and circulation-pump control.
EXTRA_SENSORS_V108 = [
    {"legacy_object_id":"palju_paluu_lampotila","name":"Palju paluu lämpötila","symbol":"GVL_HA.rTemperature_15_Palju_veden_paluu_lampotila","unit":"°C","device_class":"temperature"},
    {"legacy_object_id":"palju_poisto_lampotila","name":"Palju poisto lämpötila","symbol":"GVL_HA.rTemperature_16_Palju_veden_poisto_lampotila","unit":"°C","device_class":"temperature"},
]
for _e in EXTRA_SENSORS_V108:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["sensors"]):
        ENT["sensors"].append(_e)

EXTRA_SWITCHES_V108 = [
    {"legacy_object_id":"paljun_kiertovesipumppu","name":"Paljun kiertovesipumppu","state_symbol":"GVL_HA.xLight_055_Paljun_kiertovesipumppu","on_symbol":"GVL_HA.xCmdLightOn_055_Paljun_kiertovesipumppu","off_symbol":"GVL_HA.xCmdLightOff_055_Paljun_kiertovesipumppu","pulse":True},
]
for _e in EXTRA_SWITCHES_V108:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["switches"]):
        ENT["switches"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.8 discovery insertion point was not found")
s = s.replace(marker, insert + marker, 1)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.7 direct floor-pressure alarm",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.8 hot-tub control",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.8")
