# Changelog

## 1.3.0

- Added first Home Assistant MQTT light: OH keskivalo.
- Uses TcBA `arrLampSubscribeCommands[23].bOn` / `.bOff` for control.
- Sends momentary 200 ms command pulses and then clears the command bit.
- Reads actual lamp output state from TcBA output symbol with direct I/O ADS
  fallback (port 27908, IG 0x13003, IO 0x25B).
- Does not write directly to physical outputs.
- Retains all five v1.2.0 temperature sensors.

## 1.2.0

- Five preconfigured TcBA room temperatures.
