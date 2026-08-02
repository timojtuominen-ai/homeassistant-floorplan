# v0.3.5 diagnostic test

Keep the default settings:

```yaml
add_local_route: true
index_group: "0xF020"
index_offset: "0x40BA"
data_type: "WORD"
scale: 0.1
```

After starting the app, copy the full log beginning from:

```text
[1/7] Opening local ADS router
```

The key lines are:

```text
[3/7] Adding explicit local route ...
[5/7] Reading ADS state
[6/7] Reading ADS device info
[7/7] Reading direct ADS memory ...
```
