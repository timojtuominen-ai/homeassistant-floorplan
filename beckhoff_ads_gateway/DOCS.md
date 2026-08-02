# v0.3.3 symbol browser

After updating, open the app configuration.

Recommended first test:

```yaml
list_symbols: true
symbol_filter: ""
max_symbols: 500
```

Start the app and look for:

```text
=== ADS SYMBOL BROWSER START ===
ADS_SYMBOL name='...'
=== ADS SYMBOL BROWSER RESULT: total=... matched=... ===
```

To reduce the output, set for example:

```yaml
symbol_filter: "hvac"
```

or:

```yaml
symbol_filter: "temperature"
```

The browser can only return symbols that the TwinCAT PLC Runtime publishes
through ADS. If the connection or symbol upload fails, the log will show the
original ADS error.
