from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.9: actual final state of the automatically controlled yard lights.
EXTRA_BINARY_V109 = [
    {"legacy_object_id":"pihavalot_paalla","name":"Pihavalot päällä","symbol":"GVL_HA.xPihavalotActual","device_class":None,"invert":False},
]
for _e in EXTRA_BINARY_V109:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.9 discovery insertion point was not found")
s = s.replace(marker, insert + marker, 1)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.8 hot-tub control",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.9 yard-light actual state",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.9")
