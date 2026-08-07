# Changelog

## 1.4.0
- Added 23 primary upstairs TcBA light entities.
- Added seven room light-count sensors for floorplan use.
- Added stable `default_entity_id` for new MQTT light/count entities.
- Light states now poll every 1 second independently of 30-second temperature polling.
- Preserved the proven 200 ms TcBA `arrLampCommands` pulse method.

## 1.3.1
- Fixed OH keskivalo command target to TcBA internal `arrLampCommands[23]`.
