from pathlib import Path


p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.20: PLC v0.36 hot-tub freeze protection, garage entry-delay status
# and the Christmas-light socket's dedicated force-ON control.
EXTRA_BINARY_V120 = [
    {
        "legacy_object_id": "paljun_jaatymisenesto_aktiivinen",
        "name": "Paljun jäätymisenesto aktiivinen",
        "symbol": "GVL_HA.xPaljuFreezeProtectionActive",
        "device_class": "running",
        "invert": False,
    },
    {
        "legacy_object_id": "paljun_jaatymisenesto_pumppupyynto",
        "name": "Paljun jäätymiseneston pumppupyyntö",
        "symbol": "GVL_HA.xPaljuFreezeProtectionPumpRequest",
        "device_class": "running",
        "invert": False,
    },
    {
        "legacy_object_id": "paljun_kylma_vesi_varoitus",
        "name": "Paljun kylmä vesi -varoitus",
        "symbol": "GVL_HA.xPaljuColdWaterWarning",
        "device_class": "problem",
        "invert": False,
    },
    {
        "legacy_object_id": "paljun_jaatymisriski",
        "name": "Paljun jäätymisriski",
        "symbol": "GVL_HA.xPaljuFreezeRiskAlarm",
        "device_class": "problem",
        "invert": False,
    },
    {
        "legacy_object_id": "tallien_tuloviive",
        "name": "Tallien murtohälytyksen tuloviive",
        "symbol": "GVL_HA.xBurglaryGarageEntryDelayActive",
        "device_class": "running",
        "invert": False,
    },
    {
        "legacy_object_id": "jouluvalo_pistorasia_paalla",
        "name": "Jouluvalopistorasia päällä",
        "symbol": "GVL_HA.xJouluvaloActual",
        "device_class": "light",
        "invert": False,
    },
]
for _e in EXTRA_BINARY_V120:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)

EXTRA_SWITCHES_V120 = [
    {
        "legacy_object_id": "jouluvalot_pakko_paalle",
        "name": "Jouluvalot pakko päälle",
        "state_symbol": "GVL_HA.xJouluvaloForceOn",
        "on_symbol": "GVL_HA.xCmdJouluvaloForceOn",
        "off_symbol": "GVL_HA.xCmdJouluvaloForceOff",
        "pulse": True,
    },
]
for _e in EXTRA_SWITCHES_V120:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["switches"]):
        ENT["switches"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.20 setup insertion point was not found")
s = s.replace(marker, insert + marker, 1)

s = s.replace(
    '"sw_version":"Kotiautomaatio_TC3 v0.35.0"',
    '"sw_version":"Kotiautomaatio_TC3 v0.36"',
    1,
)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.19 kellari thermostat output",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.20 PLC v0.36 controls",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.20")
