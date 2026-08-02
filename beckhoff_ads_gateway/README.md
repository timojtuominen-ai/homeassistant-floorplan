# Beckhoff ADS Gateway v0.3.4

First direct TwinCAT Building Automation process-data test.

The app reads the living-room temperature without a PLC symbol name:

- ADS port: `801`
- Index Group: `0xF020`
- Index Offset: `0x40BA`
- Type: `WORD`
- Scale: `0.1`

Expected test result:

- raw value `264`
- Home Assistant value `26.4 °C`
