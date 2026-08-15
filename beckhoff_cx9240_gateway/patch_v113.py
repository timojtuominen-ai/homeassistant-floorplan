from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.13: outbuilding lights and garage temperature for Home Assistant.
EXTRA_LIGHTS_V113 = [
    {
        "legacy_object_id": "tallin_reunavalot",
        "name": "Tallin reunavalot",
        "state_symbol": "GVL_HA.xLight_001_Tallin_reunavalot",
        "on_symbol": "GVL_HA.xCmdLightOn_001_Tallin_reunavalot",
        "off_symbol": "GVL_HA.xCmdLightOff_001_Tallin_reunavalot",
    },
    {
        "legacy_object_id": "tallin_keskivalot",
        "name": "Tallin keskivalot",
        "state_symbol": "GVL_HA.xLight_002_Tallin_keskivalot",
        "on_symbol": "GVL_HA.xCmdLightOn_002_Tallin_keskivalot",
        "off_symbol": "GVL_HA.xCmdLightOff_002_Tallin_keskivalot",
    },
    {
        "legacy_object_id": "liiteri_etuvalot",
        "name": "Liiterin etuvalot",
        "state_symbol": "GVL_HA.xLight_003_Liiteri_etuvalot",
        "on_symbol": "GVL_HA.xCmdLightOn_003_Liiteri_etuvalot",
        "off_symbol": "GVL_HA.xCmdLightOff_003_Liiteri_etuvalot",
    },
    {
        "legacy_object_id": "liiteri_takavalo",
        "name": "Liiterin takavalo",
        "state_symbol": "GVL_HA.xLight_004_Liiteri_takavalo",
        "on_symbol": "GVL_HA.xCmdLightOn_004_Liiteri_takavalo",
        "off_symbol": "GVL_HA.xCmdLightOff_004_Liiteri_takavalo",
    },
    {
        "legacy_object_id": "tallin_wc_valo",
        "name": "Tallin WC-valo",
        "state_symbol": "GVL_HA.xLight_005_Tallin_WC_valo",
        "on_symbol": "GVL_HA.xCmdLightOn_005_Tallin_WC_valo",
        "off_symbol": "GVL_HA.xCmdLightOff_005_Tallin_WC_valo",
    },
]
for _e in EXTRA_LIGHTS_V113:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["lights"]):
        ENT["lights"].append(_e)

EXTRA_SENSORS_V113 = [
    {
        "legacy_object_id": "talli_lampotila",
        "name": "Tallin lämpötila",
        "symbol": "GVL_HA.rTemperature_01_Tallin_lampotila",
        "unit": "°C",
        "device_class": "temperature",
    },
]
for _e in EXTRA_SENSORS_V113:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["sensors"]):
        ENT["sensors"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.13 discovery insertion point was not found")
s = s.replace(marker, insert + marker, 1)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.12 sauna rate-of-rise heat detector",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.13 outbuilding lights and garage temperature",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.13")
