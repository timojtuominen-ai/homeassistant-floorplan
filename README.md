# Installation and first test

## Requirement

Install and start the **Mosquitto broker** app. Then enable the automatically discovered MQTT integration in **Settings → Devices & services**.

## Install as a local app

1. Extract the folder `beckhoff_ads_gateway` into `/addons/beckhoff_ads_gateway/`.
2. Open **Settings → Apps → App store**.
3. Open the three-dot menu and select **Check for updates**.
4. Install **Beckhoff ADS Gateway**.
5. The first build can take several minutes because `pyads` is compiled for Raspberry Pi.
6. Keep the default configuration for the first test.
7. Start the app and inspect its log.

## Defaults

- PLC IP: `192.168.1.5`
- PLC AMS Net ID: `5.14.33.10.1.1`
- Local AMS Net ID: `192.168.1.57.1.1`
- ADS port: `801`
- Symbol: `.arrHVACStates[4].lrActualValue`
- Data type: `LREAL`

When successful, MQTT Discovery creates approximately `sensor.olohuone_lampotila`.
