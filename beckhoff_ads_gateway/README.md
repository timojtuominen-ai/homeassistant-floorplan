# Beckhoff ADS Gateway v1.5.0

Adds binary sensors to the existing temperature and lighting gateway.

## Motion sensors
- Olohuone -> `P_Alerts.bLiiketunnistin1`
- Keittiö -> `P_Alerts.bLiiketunnistin2`
- Tuulikaappi -> `P_Alerts.bLiiketunnistin3`
- KHH -> `P_Alerts.bLiiketunnistin4`
- Autotalli -> `P_Alerts.bLiiketunnistin5`
- Talli -> `P_Alerts.bLiiketunnistin6`

## Terrace door
- `P_Alerts.bOviraja1`

## Leakage detectors
The BAMX Scene 7 comment lists the locations as: kitchen under sink, upstairs WC, downstairs WC, technical room. Version 1.5.0 maps LeakageDetection1..4 to that listed order.
