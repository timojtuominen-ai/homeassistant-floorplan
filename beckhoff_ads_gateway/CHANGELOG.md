# Changelog

## 1.5.0
- Added MQTT binary sensors for six motion detectors, four leakage detectors and the terrace door.
- Binary sensors are polled every 1 s by default.
- Motion detectors and terrace door use the PLC alarm logic polarity (active/open when the raw input is FALSE).
- Leakage detectors are active when the raw PLC input is TRUE.
- Added raw input value and inversion metadata to entity attributes.

## 1.4.2
- Corrected Emman / Allun room mapping.
