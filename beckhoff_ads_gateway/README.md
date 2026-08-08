# Beckhoff ADS Gateway v1.8.0

Adds one timed output for the cooker hood / ventilation exhaust reduction:

- BAM object: LampGroup 60
- Group member: Lamp 62
- ON command: `.arrLampCommands[62].bOn`
- OFF command: `.arrLampCommands[62].bOff`
- Actual output state: `.arrLampProcessOutputData[62].bData`
- Duration: 1800 seconds (30 minutes)
- Home Assistant: `switch.liesituuletin_30min`

Sending ON while it is already active restarts the 30-minute timer.
Sending OFF cancels the timer and switches the output off.
