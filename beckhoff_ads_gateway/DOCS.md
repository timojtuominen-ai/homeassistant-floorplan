# Beckhoff ADS Gateway 1.8.0

The default configuration contains nine verified temperatures, 38 TcBA light groups,
motion/door/fire/leak inputs, room light counters and the timed kitchen-hood output.

Configuration is stored in JSON arrays inside the add-on options:

- `sensors_json`: ADS values such as temperatures
- `lights_json`: TcBA pulse commands and actual lighting states
- `binary_sensors_json`: motion, door, leak and fire inputs
- `rooms_json`: room-level counts built from the configured lights
- `timed_outputs_json`: finite-duration outputs

Home Assistant preserves add-on options during an upgrade. When moving from an older
version, paste the supplied `addon_options_v1.8.0.yaml` into the add-on configuration
or reinstall the add-on to load the new defaults.

## HVAC index scan

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
