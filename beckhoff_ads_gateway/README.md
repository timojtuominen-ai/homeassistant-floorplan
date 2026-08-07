# Beckhoff ADS Gateway v1.2.0

Read-only TwinCAT 2 / TwinCAT Building Automation multi-sensor gateway.

This release includes five named TcBA room temperatures directly in the default
configuration. No HVAC scan is required.

Configured room mappings:

- Olohuone -> `.arrHVACStates[4].lrActualValue`
- Keittiö / Ruokatila -> `.arrHVACStates[7].lrActualValue`
- L&T MH -> `.arrHVACStates[5].lrActualValue`
- Allun MH (old name: Tollon huone) -> `.arrHVACStates[2].lrActualValue`
- Emman MH (old name: Vierashuone) -> `.arrHVACStates[3].lrActualValue`

The gateway reads TcBA processed `lrActualValue` values rather than raw KL3228
inputs, so Building Automation corrections are retained.

No PLC write or state-control APIs are used.
