# Changelog

## 1.7.0
- Added timed kitchen hood / ventilation exhaust-reduction control.
- Source mapping: LampGroup 60 contains Lamp 62 (Terminal 11 / channel 9).
- Home Assistant entity: `switch.liesituuletin_30min`.
- ON starts/restarts a 30-minute timer; OFF cancels it.
- State is read from the actual TcBA lamp process output.
- Timer expiry is persisted under `/data` across add-on restarts.

## 1.6.1
- Fire detector and common leakage alarm mapping update.
