# Beckhoff CX9240 Gateway — Production

Production Home Assistant add-on for Kotiautomaatio_TC3 v0.32.1 / Beckhoff CX9240.

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

Default target: CX9240 `192.168.1.171`, AMS Net ID `5.179.194.231.1.1`, ADS port `851`.

The Home Assistant diagnostic `Palohälytys kuitattu - ilmaisin edelleen aktiivinen` is intentionally omitted from production discovery. PLC acknowledgement logic remains unchanged.
