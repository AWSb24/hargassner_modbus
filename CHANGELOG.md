# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-07-01

Initial release.

### Added
- Modbus TCP integration for Hargassner pellet/wood heating systems.
- Full register map (1400+ registers) as sensors, binary sensors, selects and
  numbers, generated from the curated `MODBUS-Parameter-erweitert.csv`.
- **Component auto-detection** via master ("Nicht vorhanden"/"Vorhanden") registers:
  absent components are hidden and skipped entirely during polling (gate logic +
  read-skip).
- **Config-flow presets**: Automatisch, Basis, Komplett, Benutzerdefiniert
  (with category and per-entity selection).
- **Writable controls** limited to OEM write function codes (FC6): heating-circuit
  modes, Programmwahlschalter, buffer/boiler "Ladung starten".
- **Heating schedules** (Tages-/Wochenuhr) decoded read-only, writable via the
  `hargassner_modbus.set_schedule` service (FC16).
- Correct DAQ-ANA ×10 scaling, verified Float/Int32 high-word-first decoding,
  German enum labels, synonym/address/gate exposed as entity attributes.
- Delayed refresh after writes so new values appear quickly.
- Floorplan dashboard (under `dashboards/`) that adapts to the installation.

[0.1.0]: https://github.com/AWSb24/hargassner_modbus/releases/tag/v0.1.0
