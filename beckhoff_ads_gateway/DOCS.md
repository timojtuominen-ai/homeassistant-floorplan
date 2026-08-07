# Beckhoff ADS Gateway v1.0.0

Recommended initial configuration:

```yaml
plc_ip: 192.168.1.5
plc_ams_net_id: 5.14.33.10.1.1
local_ams_net_id: 192.168.1.57.1.1
plc_ads_port: 801

poll_interval: 30
reconnect_delay: 30
publish_heartbeat: 600
add_local_route: true

read_mode: symbol
symbol: .arrHVACStates[4].lrActualValue
symbol_data_type: LREAL

fallback_direct_read: true
index_group: "0x4040"
index_offset: "0x126270"
direct_data_type: LREAL
scale: 1.0
offset_adjustment: 0.0
precision: 1

entity_name: Olohuone lämpötila
entity_id: olohuone_lampotila
unit_of_measurement: "°C"
device_class: temperature
state_class: measurement
log_level: INFO
```

Successful operation should show:

```text
ADS connected: ...
MQTT state published: olohuone_lampotila = ... °C
```

## Existing unavailable entity

If `sensor.olohuone_lampotila` already exists from an older ADS configuration
and stays `unavailable`, remove/disable the old ADS sensor configuration or
delete the stale entity from the entity registry, then restart this app.
MQTT Discovery will then create/use the entity from this gateway.

## Read-only safety

The application does not call ADS write APIs, `write_control()`, or any PLC
state-changing operation.
