# v0.3.4 direct memory test

This release no longer uses `read_by_name()` or PLC symbol upload.

It reads the verified TcBA process-data address directly:

```yaml
index_group: "0xF020"
index_offset: "0x40BA"
data_type: "WORD"
scale: 0.1
offset_adjustment: 0.0
precision: 1
```

After updating and starting the app, inspect the log for:

```text
Direct ADS read succeeded: raw=264, scaled=26.4 °C
```

Expected Home Assistant entity:

`sensor.olohuone_lampotila`

The entity also receives diagnostic attributes containing the raw value and
the ADS address.
