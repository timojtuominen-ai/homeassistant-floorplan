# Beckhoff CX9240 Gateway — Production

Production Home Assistant add-on for Kotiautomaatio_TC3 v0.33.2 / Beckhoff CX9240.

Version 1.0.11 adds the real `switch.palokellot_off_20min` control. Switching
it ON pulses `GVL_HA.xCmdFireBellTestStart`, switching it OFF pulses
`GVL_HA.xCmdFireBellTestStop`, and its state is read back from
`GVL_HA.xFireBellTestActive`. The PLC inhibits only the physical fire-bell
output; fire detection, fire status and all other fire actions remain active.

Version 1.0.10 adds individual Home Assistant moisture entities for the
technical room, kitchen, children's WC and downstairs WC. The existing common
leak alarm remains available for acknowledgement and water-valve safety logic.

Version 1.0.9 publishes the actual final state of the main yard lights from
`GVL_HA.xPihavalotActual`. This lets the floorplan show whether the physical
lighting logic is ON while the existing force switch still controls only the
force-ON override.

Version 1.0.8 adds Home Assistant entities for the hot-tub return and outlet
temperatures and an ON/OFF switch for the hot-tub circulation pump. The PLC
continues to own the physical output and exposes its actual logical state.

Version 1.0.7 reads the floor-heating circuit low-pressure alarm directly from
`GVL_Alarm.xFloorHeatingPressureAlarm` and publishes it as
`binary_sensor.lattialammitys_paine_matala`.

Version 1.0.6 adds:

- floor-heating supply and return temperatures;
- waste-pump, battery-charger and low floor-heating-pressure alarms;
- PLC/ADS connection status, TwinCAT Runtime state and observed connection uptime;
- Raspberry Pi uptime, CPU temperature, free disk space, memory usage and throttling status when the host exposes it.

This add-on is based on the bench-tested TC3 gateway but is hard-locked to production mode. It intentionally reuses the existing `beckhoff_cx5000` MQTT namespace / legacy entity IDs where the gateway map provides them, so the existing Home Assistant floorplan can transition to the CX9240 with minimal entity-ID changes.

## Cutover rule

Do **not** run the old CX5010 `beckhoff_ads_gateway` and this CX9240 production gateway at the same time. They publish to the same production MQTT namespace and would compete for entity states.

Recommended cutover:
1. Stop the old CX5010 gateway add-on.
2. Install/start this `Beckhoff CX9240 Gateway` add-on only after CX9240 PLC Runtime 1 is online.
3. Verify ADS connection and `TC3 Gateway online`.
4. Check floorplan states: fire detectors, doors, motion, temperatures and lights.
5. If CX9240 commissioning must be aborted, stop this add-on before restarting the old CX5010 gateway.

Configure the PLC IP address and both AMS Net IDs in the add-on settings before
starting a new installation. The repository defaults use the non-routable
TEST-NET address range and are documentation placeholders only.

The Home Assistant diagnostic `Palohälytys kuitattu - ilmaisin edelleen aktiivinen` is intentionally omitted from production discovery. PLC acknowledgement logic remains unchanged.
