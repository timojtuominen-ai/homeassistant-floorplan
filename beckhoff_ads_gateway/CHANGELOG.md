# Changelog

## 0.3.4

- Replaced symbol-name reads with direct ADS Index Group/Index Offset reads.
- Added configurable data type, scaling, offset adjustment and precision.
- Added raw-value MQTT attributes.
- Configured the first verified TcBA point:
  - Port 801
  - Index Group 0xF020
  - Index Offset 0x40BA
  - WORD
  - Scale 0.1
