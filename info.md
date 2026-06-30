# Hargassner Modbus

Monitor and control a Hargassner pellet/wood heating system over **Modbus TCP**.

- 1400+ registers as sensors / binary sensors / selects / numbers
- **Auto-detects installed components** and hides/skips the rest
- Config-flow **presets**: Automatisch · Basis · Komplett · Benutzerdefiniert
- Writable heating-circuit modes & buffer/boiler charging (OEM write-FC only)
- Heating schedules (decoded; writable via `set_schedule` service)
- Floorplan dashboard that adapts to the installation

Requires Modbus enabled on the controller (ID-Card + installer param **D24 = JA**)
and Home Assistant 2024.11+.
