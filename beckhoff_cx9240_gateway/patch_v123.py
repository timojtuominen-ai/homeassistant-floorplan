from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.23: Manual HVAC summer/winter season changeover for PLC v0.36.7.
# Home Assistant exposes two buttons. The existing gateway button handler
# generates a finite BOOL pulse, and the actual selected season is always read
# back from the PLC as separate binary sensors.
EXTRA_BINARY_V123 = [
    {
        "legacy_object_id": "hvac_kesakausi",
        "name": "HVAC kesäkausi",
        "symbol": "GVL_HA.xHvacSeasonSummer",
        "device_class": None,
        "invert": False,
    },
    {
        "legacy_object_id": "hvac_talvikausi",
        "name": "HVAC talvikausi",
        "symbol": "GVL_HA.xHvacSeasonWinter",
        "device_class": None,
        "invert": False,
    },
]
for _e in EXTRA_BINARY_V123:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["binary_sensors"]):
        ENT["binary_sensors"].append(_e)

EXTRA_BUTTONS_V123 = [
    {
        "object_id": "hvac_kesakausi",
        "name": "Vaihda kesäkaudelle",
        "command_symbol": "GVL_HA.xCmdHvacSeasonSummer",
        "icon": "mdi:snowflake",
    },
    {
        "object_id": "hvac_talvikausi",
        "name": "Vaihda talvikaudelle",
        "command_symbol": "GVL_HA.xCmdHvacSeasonWinter",
        "icon": "mdi:radiator",
    },
]
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.23 setup insertion point was not found")
s = s.replace(marker, insert + marker, 1)

button_loop = '    for e in EXTRA_BUTTONS_V114: publish_button_config(e)\n'
if button_loop not in s:
    raise RuntimeError("v1.0.23 button discovery loop was not found")
s = s.replace(
    button_loop,
    button_loop + '    for e in EXTRA_BUTTONS_V123: publish_button_config(e)\n',
    1,
)

s = s.replace(
    '"sw_version":"Kotiautomaatio_TC3 v0.36.2"',
    '"sw_version":"Kotiautomaatio_TC3 v0.36.7"',
    1,
)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.22 presence simulation darkness",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.23 HVAC season controls",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.23")
