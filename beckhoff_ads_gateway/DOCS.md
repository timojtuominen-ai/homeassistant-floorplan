# Installation

1. Install and start the **Mosquitto broker** app.
2. Confirm that the MQTT integration is active.
3. Add this GitHub repository in the Home Assistant app store.
4. Install **Beckhoff ADS Gateway**.
5. Start the app and open its log.

## Required Beckhoff route

- Client AMS Net ID: `192.168.1.57.1.1`
- Client IP: `192.168.1.57`

## Initial test

- PLC IP: `192.168.1.5`
- PLC AMS Net ID: `5.14.33.10.1.1`
- ADS port: `801`
- Symbol: `.arrHVACStates[4].lrActualValue`
- Type: `LREAL`

Expected entity:

`sensor.olohuone_lampotila`
