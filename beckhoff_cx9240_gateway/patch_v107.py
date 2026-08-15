from pathlib import Path

p = Path("/app/main.py")
s = p.read_text(encoding="utf-8")

old_symbol = '"symbol":"GVL_HA.xAlarm_FloorHeatingPressure"'
new_symbol = '"symbol":"GVL_Alarm.xFloorHeatingPressureAlarm"'

if old_symbol not in s:
    raise RuntimeError("v1.0.7 floor-heating pressure source was not found")

s = s.replace(old_symbol, new_symbol, 1)
s = s.replace(
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.6 service diagnostics",
    "Starting Beckhoff CX9240 Gateway PRODUCTION v1.0.7 direct floor-pressure alarm",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched gateway main.py for v1.0.7")
