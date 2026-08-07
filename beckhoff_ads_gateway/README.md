# Beckhoff ADS Gateway v1.4.0

Adds the complete primary upstairs lighting set used by the floorplan: 23 TcBA light groups.

- Olohuone: 8 groups (20..27)
- Keittiö / ruokatila: 4 groups (31..34)
- L&T MH + VH: 3 groups (10, 12, 19)
- Allun MH: 2 groups (13, 14)
- Emman MH: 2 groups (15, 16)
- WC L&T: 2 groups (35, 36)
- WC lasten: 2 groups (38, 39)

Control uses `.arrLampCommands[n].bOn` / `.bOff` and actual state uses
`.arrLampProcessOutputData[n].bData`.

Room light-count MQTT sensors are also published. Their state is a numeric count,
and their unit is `/ total`, so Home Assistant shows e.g. `3 / 8` while the raw
state remains `3` for floorplan state filters.

Light state polling: 1 s. Temperature polling: 30 s.
