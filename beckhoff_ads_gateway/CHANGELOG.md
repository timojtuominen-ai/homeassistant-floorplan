# Changelog

## 1.3.1

- Fixed OH keskivalo command target.
- Changed control from `arrLampSubscribeCommands[23]` (mapped process input)
  to TcBA internal `arrLampCommands[23]`.
- Added command readback diagnostics.
- Actual-state feedback remains `arrLampProcessOutputData[23].bData`.

## 1.3.0

- Added first Home Assistant MQTT light: OH keskivalo.
