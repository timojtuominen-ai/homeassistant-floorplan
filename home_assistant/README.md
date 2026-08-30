# Home Assistant packages

## Presence Simulator

Copy `packages/presence_simulation.yaml` to:

```text
/config/packages/presence_simulation.yaml
```

The package keeps the existing dashboard entity ID
`switch.poissaolosimulaatio`. It requires Beckhoff CX9240 Gateway v1.0.22 or
newer, which publishes `binary_sensor.pimeaa_riittavasti` from the PLC.

After copying the package, run `ha core check` and restart Home Assistant.
