# Changelog

## 1.0.0

- Production-oriented read-only architecture.
- Persistent ADS connection.
- MQTT connection confirmation before Discovery/state publishing.
- MQTT state, attributes and availability are retained and publish-confirmed.
- Publishes only on value change, plus configurable heartbeat.
- Default polling interval increased from 5 s to 30 s.
- Reconnect backoff added.
- Primary read changed to TcBA processed `.arrHVACStates[4].lrActualValue`.
- Added verified direct LREAL fallback derived from the supplied TPY:
  `0x4040 / 0x126270`.
- Removed startup `read_state()` and `read_device_info()` diagnostics.
- No PLC write or state-control APIs are used.
