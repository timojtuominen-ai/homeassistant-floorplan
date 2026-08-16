from pathlib import Path


p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = '''

# v1.0.18: Actual downstairs room-heating demand states from PLC v0.35.0.
EXTRA_BINARY_V118 = [
    {
        "legacy_object_id": "lammityspyynto_tyohuone",
        "name": "Lämmityspyyntö työhuone",
        "symbol": "GVL_HA.xHeatDemand_06_Tyohuone_lampotila",
        "device_class": "heat",
        "invert": False,
    },
    {
        "legacy_object_id": "lammityspyynto_sauna",
        "name": "Lämmityspyyntö sauna",
        "symbol": "GVL_HA.xHeatDemand_08_Saunan_lampotila",
        "device_class": "heat",
        "invert": False,
    },
    {
        "legacy_object_id": "lammityspyynto_kylmakellari",
        "name": "Lämmityspyyntö kylmäkellari",
        "symbol": "GVL_HA.xHeatDemand_09_Kylmakellarin_lampotila",
        "device_class": "heat",
        "invert": False,
    },
    {
        "legacy_object_id": "lammityspyynto_kellari",
        "name": "Lämmityspyyntö kellari",
        "symbol": "GVL_HA.xHeatDemand_10_Kellari_lampotila",
        "device_class": "heat",
        "invert": False,
    },
]
for _e in EXTRA_BINARY_V118:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.18 setup insertion point was not found")
s = s.replace(marker, insert + marker, 1)

s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.17 room heating demand states",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.18 downstairs heating demand states",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.18")
