# Beckhoff ADS Gateway v1.6.0

Adds the 15 PLC fire detector inputs:

- `binary_sensor.palovaroitin_1` -> `P_Alerts.FireDetection1`
- ...
- `binary_sensor.palovaroitin_15` -> `P_Alerts.FireDetection15`

The PLC alarm program treats `NOT FireDetectionX` as an alarm condition.
Therefore the gateway publishes smoke/alarm ON when the raw PLC input is FALSE.

The house project does not provide reliable room names for these 15 inputs.
They are kept generically numbered so each physical detector can be identified
by pressing its test button one at a time.
