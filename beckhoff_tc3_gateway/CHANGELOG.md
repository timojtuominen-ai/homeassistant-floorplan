# Changelog

## 0.1.5
- Expand the CX9240 test gateway from the small seed map using the actual TwinCAT 3 symbol table.
- Auto-discover all `GVL_HA.xLight_*` states that have matching `xCmdLightOn_*` and `xCmdLightOff_*` command symbols.
- Auto-discover `GVL_HA.rTemperature_*` sensors.
- Auto-discover motion, door, fire/heat and leakage/water binary sensors from the `GVL_HA` interface.
- Republish MQTT Discovery after ADS runtime discovery so the additional test entities appear in Home Assistant automatically.
- Keep `test_mode: true` isolation and the known working CX9240 ADS settings.

## 0.1.2
- Remove the redundant explicit `pyads.add_route()` call on Linux. `pyads.Connection(..., ip_address)` creates the client-side route when opened.
- Keep the configured local AMS Net ID initialization before opening the PLC connection.
- Add a short TCP 48898 reachability probe so network-level failures are visible immediately in the add-on log.
- Set the bench-test defaults to the current CX9240 address `192.168.1.171` and AMS Net ID `5.179.194.231.1.1`.
