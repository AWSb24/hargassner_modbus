"""Register registry loaded from the generated registers.json.

registers.json is generated from MODBUS-Parameter.csv (see tools/gen_registers.py).
Each entry describes one Hargassner Modbus holding register:

    key, name, address, type, platform, count, encoding, scale, unit,
    device_class, state_class, writable, category, [options], [min/max/step]

The "address" is the primary Modbus address (CSV column "Adresse"); the
alternative addressing (column "Register" = address+1) is not modelled yet.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "registers.json"


@dataclass(frozen=True)
class RegisterDef:
    key: str
    name: str
    synonym: str
    address: int
    type: str
    platform: str
    count: int
    encoding: str  # int16 | int32 | float32 | bool
    scale: float
    unit: str | None
    device_class: str | None
    state_class: str | None
    writable: bool
    category: str
    basis: bool = False                  # part of the "Basis" preset
    gate: str = ""                       # synonym of the controlling master register
    gate_values: tuple[int, ...] = ()    # gate values that enable this register
    options: dict[int, str] | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None

    @property
    def options_by_label(self) -> dict[str, int]:
        return {v: k for k, v in (self.options or {}).items()}


@lru_cache(maxsize=1)
def all_registers() -> dict[str, RegisterDef]:
    """Return every register defined in registers.json keyed by ``key``."""
    raw = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    result: dict[str, RegisterDef] = {}
    for item in raw:
        opts = item.get("options")
        options = {int(k): v for k, v in opts.items()} if opts else None
        result[item["key"]] = RegisterDef(
            key=item["key"],
            name=item["name"],
            synonym=item.get("synonym", ""),
            address=item["address"],
            type=item["type"],
            platform=item["platform"],
            count=item["count"],
            encoding=item["encoding"],
            scale=item.get("scale", 1) or 1,
            unit=item.get("unit"),
            device_class=item.get("device_class"),
            state_class=item.get("state_class"),
            writable=item.get("writable", False),
            category=item.get("category", "allgemein"),
            basis=item.get("basis", False),
            gate=item.get("gate", ""),
            gate_values=tuple(item.get("gate_values", [])),
            options=options,
            min=item.get("min"),
            max=item.get("max"),
            step=item.get("step"),
        )
    return result


@lru_cache(maxsize=1)
def categories() -> list[str]:
    """All categories present, sorted."""
    return sorted({r.category for r in all_registers().values()})


def registers_in_categories(enabled_categories: set[str]) -> list[RegisterDef]:
    """All instantiable registers belonging to the enabled categories.

    "unsupported" platforms (schedules / bitfields) are always excluded for now.
    Sorted by display name for use in the entity selection form.
    """
    out = [
        reg
        for reg in all_registers().values()
        if reg.platform != "unsupported" and reg.category in enabled_categories
    ]
    return sorted(out, key=lambda r: r.name.lower())


def active_registers(
    enabled_categories: set[str], excluded_keys: set[str]
) -> list[RegisterDef]:
    """Registers to instantiate: everything in the enabled categories, minus any
    individually excluded keys (optional fine-grained de-selection)."""
    return [
        reg
        for reg in registers_in_categories(enabled_categories)
        if reg.key not in excluded_keys
    ]


def all_categories_registers() -> list[RegisterDef]:
    """Every instantiable register (all categories)."""
    return [r for r in all_registers().values() if r.platform != "unsupported"]


def basis_registers() -> list[RegisterDef]:
    """Registers flagged as part of the 'Basis' preset (CSV 'Basis' column)."""
    return [
        r for r in all_registers().values()
        if r.platform != "unsupported" and r.basis
    ]
