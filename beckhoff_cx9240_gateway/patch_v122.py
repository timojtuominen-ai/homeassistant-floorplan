from pathlib import Path


p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.22: Publish the PLC's established outdoor-light darkness condition for
# Home Assistant presence simulation. The PLC remains the single source of
# truth for the light-level threshold and hysteresis.
EXTRA_BINARY_V122 = [
    {
        "legacy_object_id": "pimeaa_riittavasti",
        "name": "Pimeää riittävästi",
        "symbol": "GVL_HA.xPihavalotDarkEnough",
        "device_class": None,
        "invert": False,
    },
]
for _e in EXTRA_BINARY_V122:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.22 setup insertion point was not found")
s = s.replace(marker, insert + marker, 1)

s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.21 PLC v0.36.2 shell and cabinet",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.22 presence simulation darkness",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.22")
