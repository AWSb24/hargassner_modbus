# Hargassner Modbus – Home Assistant Integration

Custom integration to read and control a Hargassner heating system over **Modbus TCP**.

## Installation
1. Copy the `hargassner_modbus` folder into `config/custom_components/` of your Home Assistant instance.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → "Hargassner Modbus"**.
4. Enter the **IP address**, **port** (default `502`) and **unit/slave ID** (default `1`).

Requirements on the controller (per the V07 manual):
- ModBus ID-Card inserted.
- Installer parameter **D24 "ModBus aktiviert" = JA**.

## What gets created
Entities are organised **purely by category** (no fixed core set). During setup you pick
which categories apply to your installation:

1. **Step 1 – network:** IP / port / slave (connection test).
2. **Step 2 – categories:** multi-select of the ~30 categories (e.g. `kessel`, `puffer`,
   only the `heizkreis_X` you actually have, `boiler_1`, `mbus_wmz`, …). Default = a
   recommended base (`kessel`, `puffer`, `zentralpuffer`, `witterung`). **No selection =
   no entities.** A checkbox enables the optional step 3.
3. **Step 3 – entities (optional):** every entity of the chosen categories is pre-selected
   in a searchable dropdown; remove the ones you don't need.

You can change all of this later via **Configure** (options flow), which also exposes the
polling interval. Registers belonging to hardware that isn't installed report `unavailable`.

The full register map (1412 registers, generated from `MODBUS-Parameter.csv`) ships in
`registers.json`; `const.py → RECOMMENDED_CATEGORIES` only sets the step-2 default.

## Design decisions
- **Addressing:** the CSV column *"Adresse"* is used as the real Modbus address (confirmed
  against the user's Node-RED flow). The alternative addressing (column *"Register"* = address+1)
  is not modelled yet.
- **Write policy (conservative):** only registers that carry an explicit OEM write function
  code (FC6) are made writable. `rw`-flagged registers without a write FC stay **read-only**.
- **Datatypes:** Integer/Auswahl = 1 register, Float/Int32 = 2 registers, Tagesprogramm = 4,
  Wochenprogramm = 5 (schedules and bitfields are parsed but not yet exposed → `platform:
  "unsupported"`).
- **⚠ 32-bit word order is unverified.** Float/Int32 are decoded **high word first**
  (`const.WORD_ORDER_BIG = True`). After the first live read, check a known Float value
  (e.g. a Raumtemperatur setpoint). If it looks wrong, set `WORD_ORDER_BIG = False`.

## Schedules (Tages-/Wochenuhr)
TPROG/WPROG registers are shown as read-only sensors (state e.g. `Mo, Di: 06:00–22:00`,
with `start_1/stop_1/start_2/stop_2`/`days` attributes). They are **writable via the
service** `hargassner_modbus.set_schedule` (FC16). Only the fields you pass are changed;
the rest keep their current value. A window with start == stop is disabled.

```yaml
service: hargassner_modbus.set_schedule
target:
  entity_id: sensor.hargassner_heizung_heizkreis_1_wochenuhr_1
data:
  start_1: "06:00"
  stop_1: "22:00"
  days: ["Mo", "Di", "Mi", "Do", "Fr"]
```

Schedule writes are also subject to the controller's remote-control lock (Sperrdauer).

## Regenerating the register map
`registers.json` is generated from `../../MODBUS-Parameter.csv`:

```bash
python custom_components/hargassner_modbus/tools/gen_registers.py
```

## Roadmap
- Expose BITFIELD registers (currently `platform: "unsupported"`).
- Optional support for the alternative register addressing.
- System schematic dashboard.
