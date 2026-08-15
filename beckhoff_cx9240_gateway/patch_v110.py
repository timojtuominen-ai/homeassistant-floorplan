from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.10: four independent moisture detectors from PLC v0.33.0.
EXTRA_BINARY_V110 = [
    {"legacy_object_id":"kosteusvahti_tekninen_tila","name":"Kosteusvahti tekninen tila","symbol":"GVL_HA.xMoisture_TechnicalRoom","device_class":"moisture","invert":False},
    {"legacy_object_id":"kosteusvahti_keittio","name":"Kosteusvahti keittiö","symbol":"GVL_HA.xMoisture_Kitchen","device_class":"moisture","invert":False},
    {"legacy_object_id":"kosteusvahti_lasten_wc","name":"Kosteusvahti lasten WC","symbol":"GVL_HA.xMoisture_ChildrensWC","device_class":"moisture","invert":False},
    {"legacy_object_id":"kosteusvahti_alakerran_wc","name":"Kosteusvahti alakerran WC","symbol":"GVL_HA.xMoisture_DownstairsWC","device_class":"moisture","invert":False},
]
for _e in EXTRA_BINARY_V110:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.10 discovery insertion point was not found")
s = s.replace(marker, insert + marker, 1)
s = s.replace(
    '"sw_version":"Kotiautomaatio_TC3 v0.32.1"',
    '"sw_version":"Kotiautomaatio_TC3 v0.33.0"',
    1,
)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.9 yard-light actual state",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.10 independent moisture detectors",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.10")
