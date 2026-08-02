# Installation

1. Install and start **Mosquitto broker** in Home Assistant.
2. Ensure the MQTT integration is active.
3. Add this GitHub repository to:
   **Settings → Apps → App store → Repositories**
4. Install **Beckhoff ADS Gateway**.
5. Start it and inspect the log.

## Required Beckhoff route

- Client AMS Net ID: `192.168.1.57.1.1`
- Client IP: `192.168.1.57`

## Expected first entity

`sensor.olohuone_lampotila`
