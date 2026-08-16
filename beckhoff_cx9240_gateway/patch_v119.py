from pathlib import Path


p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

insert = '''

# v1.0.19: Kellari floorplan follows the actual physical thermostat output.
for _e in ENT["binary_sensors"]:
    if _e.get("legacy_object_id") == "lammityspyynto_kellari":
        _e["name"] = "Kellarin termostaattilähtö"
        _e["symbol"] = "GVL_IO.xDO_Toimilaite_Kellari"
        _e["device_class"] = "heat"
        _e["invert"] = False
        break
else:
    raise RuntimeError("v1.0.19 kellari heating entity was not found")
'''

marker = "\ndef setup_discovery():"
if marker not in s:
    raise RuntimeError("v1.0.19 setup insertion point was not found")
s = s.replace(marker, insert + marker, 1)

s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.18 downstairs heating demand states",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.19 kellari thermostat output",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.19")
