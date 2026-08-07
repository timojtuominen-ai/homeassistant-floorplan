# Changelog

## 1.6.1
- Named FireDetection 1..15 from the house electrical memo "Hälytin tulot" sheet.
- Upper floor mapping: 11 L&T MH, 12 Keittiö, 13 Olohuone, 14 Allun MH, 15 Emman MH.
- Corrected leakage monitoring: the physical alarm-input list has one common moisture input for kitchen / downstairs WC / upstairs WC / technical room.
- Removed the four misleading per-room leakage MQTT entities from v1.5.0/v1.6.0 and added one `vuotovahti_yhteinen` entity.
- Existing motion-sensor and terrace-door mappings are unchanged.
