# Beckhoff ADS Gateway v1.0.0

Read-only Home Assistant gateway for TwinCAT 2 / TwinCAT Building Automation (TcBA).

## Important

This release contains no PLC write or state-change commands. It only reads ADS data.

The default primary value is the TcBA processed HVAC room temperature:

`.arrHVACStates[4].lrActualValue`

This is preferred over the KL3228 raw input because the TcBA value is intended
to reflect the Building Automation processing, including configured correction
logic.

A project-specific direct fallback is included from the supplied TPY file:

- Index Group: `0x4040`
- Index Offset: `0x126270`
- Type: `LREAL`

That address corresponds to `arrHVACStates[4].lrActualValue` in this project.

## Behaviour

- one persistent ADS connection
- 30 second polling by default
- publishes MQTT only when the value changes (plus 10 minute heartbeat)
- retained MQTT state and availability
- graceful reconnect with 30 second backoff
- MQTT publish confirmation in the log
