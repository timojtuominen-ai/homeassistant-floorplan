from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.12: sauna PT1000 rate-of-rise heat detector from PLC v0.34.0.
EXTRA_BINARY_V112 = [
    {
        "legacy_object_id":"palovaroitin_16",
        "name":"Saunan lämpöilmaisin (10 °C/min)",
        "symbol":"GVL_HA.xAlarm_FireDetection16",
        "device_class":"heat",
        "invert":False,
    },
]
for _e in EXTRA_BINARY_V112:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.12 discovery insertion point was not found")
s = s.replace(marker, insert + marker, 1)
s = s.replace(
    '"sw_version":"Kotiautomaatio_TC3 v0.33.2"',
    '"sw_version":"Kotiautomaatio_TC3 v0.34.0"',
    1,
)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.11 fire-bell inhibit control",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.12 sauna rate-of-rise heat detector",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.12")
