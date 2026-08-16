from pathlib import Path


p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = '''

# v1.0.17: Actual room-heating demand states from PLC v0.35.0.
EXTRA_BINARY_V117 = [
    {
        "legacy_object_id": "lammityspyynto_emman_huone",
        "name": "Lämmityspyyntö Emman huone",
        "symbol": "GVL_HA.xHeatDemand_02_Emman_huone_lampotila",
        "device_class": "heat",
        "invert": False,
    },
    {
        "legacy_object_id": "lammityspyynto_allun_huone",
        "name": "Lämmityspyyntö Allun huone",
        "symbol": "GVL_HA.xHeatDemand_03_Allun_huone_lampotila",
        "device_class": "heat",
        "invert": False,
    },
    {
        "legacy_object_id": "lammityspyynto_olohuone",
        "name": "Lämmityspyyntö olohuone",
        "symbol": "GVL_HA.xHeatDemand_04_Olohuone_lampotila",
        "device_class": "heat",
        "invert": False,
    },
    {
        "legacy_object_id": "lammityspyynto_lt_mh",
        "name": "Lämmityspyyntö L&T MH",
        "symbol": "GVL_HA.xHeatDemand_05_Makuuhuone_L_ja_T_lampotila",
        "device_class": "heat",
        "invert": False,
    },
    {
        "legacy_object_id": "lammityspyynto_keittio",
        "name": "Lämmityspyyntö keittiö",
        "symbol": "GVL_HA.xHeatDemand_07_Ruokatila_lampotila",
        "device_class": "heat",
        "invert": False,
    },
]
for _e in EXTRA_BINARY_V117:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.17 setup insertion point was not found")
s = s.replace(marker, insert + marker, 1)

s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.16 Shelly fire output and lifetime counters",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.17 room heating demand states",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.17")
