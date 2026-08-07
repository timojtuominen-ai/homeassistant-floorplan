# Beckhoff ADS Gateway v1.3.0

This test release keeps the five working TcBA room-temperature sensors and adds
one Home Assistant light entity:

- **OH keskivalo**
- TcBA lamp index: **23**
- ON command: `.arrLampSubscribeCommands[23].bOn`
- OFF command: `.arrLampSubscribeCommands[23].bOff`
- Command type: BOOL pulse, 200 ms
- Preferred state: `.arrLampProcessOutputData[23].bData`
- State fallback: ADS I/O server port 27908, IG `0x13003`, IO `0x25B`

The light is deliberately implemented through TcBA's command interface, not by
writing directly to the physical output.

Only this single test light is writable in v1.3.0. Temperature sensors remain
read-only.
