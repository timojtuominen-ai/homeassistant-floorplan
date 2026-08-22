from pathlib import Path


p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.21: PLC v0.36.2 removed the local floor-heating supply/return PT1000
# measurements. Remove their reads before polling so a missing ADS symbol cannot
# disconnect the whole gateway. T15/ch2 is now the electrical-cabinet PT1000;
# T15/ch3 is a raw spare and is deliberately not published.
_REMOVED_SENSOR_IDS_V121 = {
    "lattialammitys_meno_lampotila",
    "lattialammitys_paluu_lampotila",
}
ENT["sensors"] = [
    _e for _e in ENT["sensors"]
    if _e.get("legacy_object_id") not in _REMOVED_SENSOR_IDS_V121
]

_REMOVED_NUMBER_IDS_V121 = {
    "lattialammitys_meno_offset",
    "lattialammitys_paluu_offset",
}
NUMBERS[:] = [
    _e for _e in NUMBERS
    if _e.get("id") not in _REMOVED_NUMBER_IDS_V121
]

EXTRA_SENSORS_V121 = [
    {
        "legacy_object_id": "sahkokaapin_lampotila",
        "name": "Sähkökaapin lämpötila",
        "symbol": "GVL_HA.rTemperature_11_Sahkokaapin_lampotila",
        "unit": "°C",
        "device_class": "temperature",
    },
]
for _e in EXTRA_SENSORS_V121:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["sensors"]):
        ENT["sensors"].append(_e)

EXTRA_NUMBERS_V121 = [
    {
        "id": "sahkokaappi_temperature_offset",
        "name": "Sähkökaapin lämpötila offset",
        "symbol": "GVL_HA.rOffset_11_Sahkokaapin_lampotila",
        "min": -15.0,
        "max": 15.0,
        "step": 0.1,
        "unit": "°C",
    },
]
for _e in EXTRA_NUMBERS_V121:
    if not any(x.get("id") == _e["id"] for x in NUMBERS):
        NUMBERS.append(_e)

EXTRA_BINARY_V121 = [
    {
        "legacy_object_id": "sahkokaapin_lampoilmaisin",
        "name": "Sähkökaapin lämpöilmaisin",
        "symbol": "GVL_HA.xFire_17_Sahkokaapin_lampoilmaisin",
        "device_class": "heat",
        "invert": False,
    },
    {
        "legacy_object_id": "kuorivalvonta_kytkentavalmis",
        "name": "Kuorivalvonta kytkentävalmis",
        "symbol": "GVL_HA.xShellProtectionArmingReady",
        "device_class": None,
        "invert": False,
    },
    {
        "legacy_object_id": "kuorivalvonta_kytkenta_estetty",
        "name": "Kuorivalvonnan kytkentä estetty",
        "symbol": "GVL_HA.xShellProtectionArmingBlocked",
        "device_class": "problem",
        "invert": False,
    },
    {
        "legacy_object_id": "kuorivalvonta_tuloviive",
        "name": "Kuorivalvonnan tuloviive",
        "symbol": "GVL_HA.xShellProtectionEntryDelayActive",
        "device_class": "running",
        "invert": False,
    },
]
for _e in EXTRA_BINARY_V121:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)

EXTRA_SWITCHES_V121 = [
    {
        "legacy_object_id": "kuorivalvonta",
        "name": "Kuorivalvonta",
        "state_symbol": "GVL_HA.xShellProtectionArmed",
        "on_symbol": "GVL_HA.xCmdShellProtectionArm",
        "off_symbol": "GVL_HA.xCmdShellProtectionDisarm",
        "pulse": True,
    },
]
for _e in EXTRA_SWITCHES_V121:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["switches"]):
        ENT["switches"].append(_e)

def cleanup_removed_floor_temperature_discovery_v121():
    # Delete retained MQTT Discovery configs so the removed PLC measurements
    # disappear cleanly instead of remaining as permanently unavailable entities.
    _topics = [
        "homeassistant/sensor/beckhoff_ads/lattialammitys_meno_lampotila/config",
        "homeassistant/sensor/beckhoff_ads/lattialammitys_paluu_lampotila/config",
        "homeassistant/number/beckhoff_cx9240/lattialammitys_meno_offset/config",
        "homeassistant/number/beckhoff_cx9240/lattialammitys_paluu_offset/config",
    ]
    for _topic in _topics:
        mqttc.publish(_topic, b"", retain=True)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.21 setup insertion point was not found")
s = s.replace(marker, insert + marker, 1)

setup_marker = "def setup_discovery():\n    if not DISCOVERY:return"
setup_replacement = (
    "def setup_discovery():\n"
    "    if not DISCOVERY:return\n"
    "    cleanup_removed_floor_temperature_discovery_v121()"
)
if setup_marker not in s:
    raise RuntimeError("v1.0.21 setup body was not found")
s = s.replace(setup_marker, setup_replacement, 1)

s = s.replace(
    '"sw_version":"Kotiautomaatio_TC3 v0.36"',
    '"sw_version":"Kotiautomaatio_TC3 v0.36.2"',
    1,
)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.20 PLC v0.36 controls",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.21 PLC v0.36.2 shell and cabinet",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.21")
