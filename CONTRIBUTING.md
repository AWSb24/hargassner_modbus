# Contributing

Thanks for helping improve the Hargassner Modbus integration!

## Project layout
```
custom_components/hargassner_modbus/   the integration
  ├─ registers.json                    generated register map (shipped)
  ├─ tools/gen_registers.py            generator
  └─ …
MODBUS-Parameter-erweitert.csv          curated source of truth (single source)
dashboards/                             Floorplan dashboard (SVG + YAML)
```

## The register map
`registers.json` is **generated** — do not edit it by hand. The single source of
truth is `MODBUS-Parameter-erweitert.csv`, which carries, per register:

- `Synonym`, `Kategorie`, `Beschreibung`, `Typ`, `Registertyp schreiben`,
  `Multiplikator`, `Unit`, `Min/Max/Inc`, enum labels (`0`..`20`)
- `Basis` — flag for the "Basis" preset
- `Gate` / `Gate-aktiv-bei` — the component-presence hierarchy: a register is shown
  and polled only if its gate (a master "vorhanden" register, referenced by synonym)
  is one of the listed values. Chains cascade (child → master → top master).

After editing the CSV, regenerate:

```bash
python custom_components/hargassner_modbus/tools/gen_registers.py
```

Keep the CSV consistent: every `Gate` must reference an existing `Synonym`, no
cycles, `Gate-aktiv-bei` indices must exist in the gate's enum.

## Write policy
Writing is intentionally conservative — only registers with an OEM write function
code (FC6) become writable entities; schedules use FC16 via the `set_schedule`
service. Do not widen this without explicit per-register review.

## Style
Match the surrounding code. Keep changes small and focused; run a quick import check:

```bash
python -c "import importlib; [importlib.import_module('custom_components.hargassner_modbus.'+m) for m in ['__init__','config_flow','coordinator','registers','sensor','select','number','binary_sensor','services','modbus_hub','entity','const']]"
```

## Pull requests
- Describe what changed and why; reference any affected registers by synonym/address.
- Update `CHANGELOG.md` under an "Unreleased" section.
- The `Validate` workflow (hassfest + HACS) must pass.
