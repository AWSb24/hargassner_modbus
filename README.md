# Hargassner Modbus – Home Assistant Integration

[![hacs][hacs-badge]][hacs] [![validate][validate-badge]][validate]

Control and monitor a **Hargassner** pellet/wood heating system in Home Assistant
over **Modbus TCP**. The integration ships the full register map and adapts itself
to your installation: components that aren't installed are detected and hidden
automatically.

## Features
- **1400+ registers** from the OEM Modbus map as sensors, binary sensors, selects
  and numbers (curated `registers.json`).
- **Auto-detection of installed components** – each component has a master
  "vorhanden" register; absent components are hidden *and not polled* (saves
  requests and avoids illegal-address errors).
- **Presets** in the config flow:
  - **Automatisch** – all categories, only the components you actually have.
  - **Basis** – a small curated core set.
  - **Komplett** – literally everything (incl. not-installed, shown unavailable).
  - **Benutzerdefiniert** – pick categories and individual entities.
- **Writable controls** (conservative, OEM write-FC only): heating-circuit modes,
  Programmwahlschalter, buffer/boiler "Ladung starten".
- **Heating schedules** (Tages-/Wochenuhr) shown decoded; writable via the
  `hargassner_modbus.set_schedule` service (FC16).
- **Correct scaling** (DAQ-ANA fixed-point ×10), verified Float/Int32 word order,
  German enum labels.
- A ready **Floorplan dashboard** that auto-adapts to the installation
  (see [`dashboards/`](dashboards/)).

## Requirements
- Modbus must be enabled on the controller: ID-Card inserted and installer
  parameter **D24 "ModBus aktiviert" = JA**.
- Home Assistant 2024.11 or newer.

## Installation (HACS)
1. HACS → Integrations → ⋮ → **Custom repositories** → add this repository
   (`https://github.com/AWSb24/hargassner_modbus`), category **Integration**.
2. Install **Hargassner Modbus**, then restart Home Assistant.
3. **Settings → Devices & Services → Add Integration → Hargassner Modbus**.
4. Enter IP / port (default 502) / unit-ID (default 1), then choose a preset.

### Manual installation
Copy `custom_components/hargassner_modbus` into your `config/custom_components/`
folder and restart Home Assistant.

## Configuration
Everything is set in the UI (config + options flow): network data, preset, polling
interval, and – for the custom preset – categories and individual entities. After a
hardware change, reload the integration so it re-detects the installed components.

## Dashboard
The [`dashboards/`](dashboards/) folder contains a Floorplan schematic (requires the
HACS *Floorplan* card) that shows live values and hides not-installed components.

## Notes
- **Remote-control lock:** the controller blocks Modbus writes for a configurable
  period after any interaction at its display (Sperrdauer für Fernsteuerung). If a
  write returns "illegal data value", check that lock first.
- Writing is intentionally limited to OEM-sanctioned write registers.

## Development
`registers.json` is generated from the curated `MODBUS-Parameter-erweitert.csv`:

```bash
python custom_components/hargassner_modbus/tools/gen_registers.py
```

## Disclaimer
Not affiliated with or endorsed by Hargassner. Use at your own risk – writing to a
biomass boiler can have physical consequences.

[hacs]: https://github.com/hacs/integration
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[validate]: ../../actions/workflows/validate.yml
[validate-badge]: ../../actions/workflows/validate.yml/badge.svg
