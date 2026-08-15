from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = r'''

# v1.0.11: physical fire-bell inhibit control from Home Assistant.
# ON and OFF are pulse commands; the switch state always comes back from the PLC.
EXTRA_SWITCHES_V111 = [
    {
        "legacy_object_id":"palokellot_off_20min",
        "name":"Palokellot OFF 20 min",
        "state_symbol":"GVL_HA.xFireBellTestActive",
        "on_symbol":"GVL_HA.xCmdFireBellTestStart",
        "off_symbol":"GVL_HA.xCmdFireBellTestStop",
        "pulse":True,
    },
]
for _e in EXTRA_SWITCHES_V111:
    if not any(x.get("legacy_object_id") == _e["legacy_object_id"] for x in ENT["switches"]):
        ENT["switches"].append(_e)
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.11 discovery insertion point was not found")
s = s.replace(marker, insert + marker, 1)
s = s.replace(
    '"sw_version":"Kotiautomaatio_TC3 v0.33.0"',
    '"sw_version":"Kotiautomaatio_TC3 v0.33.2"',
    1,
)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.10 independent moisture detectors",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.11 fire-bell inhibit control",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.11")
