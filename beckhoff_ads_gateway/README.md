# Beckhoff ADS Gateway v1.3.1

Test release for the first controllable light: **OH keskivalo**.

## Important correction from v1.3.0

v1.3.0 wrote to:

- `.arrLampSubscribeCommands[23].bOn`
- `.arrLampSubscribeCommands[23].bOff`

Those variables are mapped TwinCAT task **inputs** (`%IB...`) intended for
subscribed/network commands.

v1.3.1 instead writes to TcBA's internal lamp command array:

- ON: `.arrLampCommands[23].bOn`
- OFF: `.arrLampCommands[23].bOff`

The actual light state is still read from:

- `.arrLampProcessOutputData[23].bData`

The command is a short BOOL pulse and v1.3.1 logs command-symbol readback while
the pulse is asserted and again after it is cleared.

Only OH keskivalo is writable in this test version.
