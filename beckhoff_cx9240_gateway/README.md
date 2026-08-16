# Beckhoff CX9240 Gateway — Production

Version 1.0.18 publishes the actual downstairs PLC room-heating demand states used by the floorplan:

- `binary_sensor.lammityspyynto_tyohuone`
- `binary_sensor.lammityspyynto_sauna`
- `binary_sensor.lammityspyynto_kylmakellari`
- `binary_sensor.lammityspyynto_kellari`

These entities read the PLC-owned `GVL_HA.xHeatDemand_06/08/09/10_*` BOOL interfaces. The gateway only publishes their state.

Version 1.0.17 publishes the actual PLC room-heating demand states used by the upstairs floorplan:

- `binary_sensor.lammityspyynto_emman_huone`
- `binary_sensor.lammityspyynto_allun_huone`
- `binary_sensor.lammityspyynto_olohuone`
- `binary_sensor.lammityspyynto_lt_mh`
- `binary_sensor.lammityspyynto_keittio`

The entities read the PLC-owned `GVL_HA.xHeatDemand_*` BOOL interfaces. The gateway only publishes their state; it does not calculate or command room heating.

Production Home Assistant add-on for Kotiautomaatio_TC3 v0.34.1 / Beckhoff CX9240.

Version 1.0.15 removes retained MQTT Discovery configurations left by the
obsolete `beckhoff_cx5000` gateway device. These retained messages created a
second `Beckhoff CX9240` device and duplicate entities such as
`light.beckhoff_cx9240_keittio_valitila_valo`. The cleanup targets only the old
Discovery namespace; the active `beckhoff_ads` entities and their established
entity IDs remain unchanged.

Version 1.0.14 adds four momentary lighting group buttons and two stateful
cleaning-light switches:

- `button.kaikki_valot_pois`
- `button.alakerran_valot_pois`
- `button.ylakerran_valot_pois`
- `button.tallin_liiterin_valot_pois`
- `switch.siivousvalot_alakerta`
- `switch.siivousvalot_ylakerta`

All group-off commands are handled by the PLC. They leave the main yard lights,
walkway lights and extra yard lights untouched. Fire-alarm lighting has priority.
PLC v0.34.1 also filters the sauna software heat detector to reject short steam
spikes while retaining rate-of-rise and fixed high-temperature protection.

Version 1.0.13 publishes the five outbuilding lights and garage temperature:

- `light.tallin_reunavalot`
- `light.tallin_keskivalot`
- `light.tallin_wc_valo`
- `light.liiteri_etuvalot`
- `light.liiteri_takavalo`
- `sensor.talli_lampotila`

The light commands use the existing PLC-owned `GVL_HA.xCmdLightOn_001...005`
and `GVL_HA.xCmdLightOff_001...005` interfaces. Their states are read from
`GVL_HA.xLight_001...005`; the gateway never writes physical outputs directly.

Version 1.0.12 publishes the sauna PT1000 10 °C/min rate-of-rise detector as
`binary_sensor.palovaroitin_16`. The detector is calculated and latched by the
PLC; the gateway only exposes its raw detector state to Home Assistant.

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
