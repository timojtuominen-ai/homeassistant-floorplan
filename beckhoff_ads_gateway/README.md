# Beckhoff ADS Gateway v0.3.5

Focused ADS route and connection diagnostics.

The application performs seven logged steps:

1. Open the local ADS router
2. Set the local AMS Net ID
3. Add an explicit Linux-side route to the PLC
4. Open the PLC ADS connection
5. Read ADS state
6. Read ADS device information
7. Read the verified TcBA memory address directly

Verified test point:

- ADS port: `801`
- Index Group: `0xF020`
- Index Offset: `0x40BA`
- Type: `WORD`
- Scale: `0.1`
