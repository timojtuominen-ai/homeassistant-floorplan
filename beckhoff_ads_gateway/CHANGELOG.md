# Changelog

## 1.2.0

- Added five preconfigured room-temperature sensors.
- Removed the need for HVAC scanning for the known upstairs rooms.
- Uses TcBA processed `lrActualValue` for all room temperatures.
- Keeps one persistent ADS connection for all sensors.
- MQTT Discovery creates one Home Assistant entity per room.
- No PLC write or state-control commands.

## 1.1.0

- Added multi-sensor support using `sensors_json`.
- Added optional read-only TcBA HVAC state scanner.
