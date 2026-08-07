# v1.1.0 multi-sensor configuration

Default `sensors_json` contains the verified living-room symbol only. Do not guess other room indices.

To identify them safely, temporarily set:

```yaml
scan_hvac_states: true
scan_start_index: 0
scan_end_index: 31
```

Restart the app and copy the log section between `TcBA HVAC STATE SCAN` and `SCAN END`. The scanner only reads LREAL values and does not publish scan results as Home Assistant entities.

Once indices are identified, add objects to `sensors_json`, for example:

```json
[{"id":"olohuone_lampotila","name":"Olohuone lämpötila","symbol":".arrHVACStates[4].lrActualValue","type":"LREAL","unit":"°C","device_class":"temperature","state_class":"measurement","precision":1}]
```
