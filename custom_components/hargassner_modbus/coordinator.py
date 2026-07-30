"""DataUpdateCoordinator that polls the Hargassner controller."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import WORD_ORDER_BIG, WRITE_REFRESH_DELAY
from .modbus_hub import (
    HargassnerHub,
    ModbusConnectionError,
    ModbusDataError,
    decode,
    decode_schedule,
)
from .registers import RegisterDef

_LOGGER = logging.getLogger(__name__)


class HargassnerCoordinator(DataUpdateCoordinator[dict[str, object]]):
    """Polls all active registers and exposes decoded values by key."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        hub: HargassnerHub,
        registers: list[RegisterDef],
        scan_interval: int,
        gate_filter: bool = True,
        request_delay: float = 0.0,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="Hargassner Modbus",
            update_interval=timedelta(seconds=scan_interval),
        )
        self.config_entry = entry
        self.hub = hub
        self.registers = registers
        # optional pause (seconds) between individual reads to relieve the controller
        self._request_delay = request_delay
        # When True, only entities of installed components (gate active) are
        # created; when False, every selected register gets an entity.
        self.gate_filter = gate_filter
        self.reg_by_key = {r.key: r for r in registers}
        self._syn2key = {r.synonym: r.key for r in registers if r.synonym}
        self.gate_active: dict[str, bool] = {}
        # Read masters before their dependents so an inactive subtree can be
        # skipped (one Modbus request per register; the controller rejects blocks
        # that contain an undefined address, so we never merge registers).
        self._read_order = sorted(registers, key=self._gate_depth)
        _LOGGER.debug("Polling %d registers (gate-ordered)", len(registers))

    def should_create(self, reg: RegisterDef) -> bool:
        """Whether an entity should be created for this register.

        With gate_filter on, registers of a not-installed component (gate
        inactive after the first poll) are not instantiated at all.
        """
        return not self.gate_filter or self.gate_active.get(reg.key, True)

    def _gate_depth(self, reg: RegisterDef) -> int:
        """Length of the register's gate chain (0 = no gate)."""
        depth = 0
        cur = reg
        seen: set[str] = set()
        while cur.gate and cur.key not in seen:
            seen.add(cur.key)
            gate_key = self._syn2key.get(cur.gate)
            if gate_key is None:
                break
            cur = self.reg_by_key[gate_key]
            depth += 1
        return depth

    async def _async_update_data(self) -> dict[str, object]:
        data: dict[str, object] = {}
        gate_active: dict[str, bool] = {}
        ok = conn_errors = skipped = 0
        attempted = False

        for reg in self._read_order:
            if not self._gate_allows_read(reg, data, gate_active):
                gate_active[reg.key] = False
                data[reg.key] = None
                skipped += 1
                continue
            gate_active[reg.key] = True
            if self._request_delay and attempted:
                await asyncio.sleep(self._request_delay)  # pause between reads
            attempted = True
            try:
                raw = await self.hub.read_block(reg.address, reg.count)
            except ModbusDataError:
                # Defined but not readable (e.g. not installed): mark missing.
                data[reg.key] = None
                continue
            except ModbusConnectionError as err:
                conn_errors += 1
                data[reg.key] = None
                _LOGGER.debug("Connection error reading %s: %s", reg.address, err)
                continue
            ok += 1
            data[reg.key] = self._decode_register(reg, raw)

        self.gate_active = gate_active
        if ok == 0:
            raise UpdateFailed(
                f"No registers could be read ({conn_errors} connection errors)"
            )
        if skipped:
            _LOGGER.debug("Skipped %d registers via gate logic", skipped)
        return data

    def _gate_allows_read(self, reg, data, gate_active) -> bool:
        """Whether ``reg`` should be read, given its master's value.

        Processed in gate-depth order, so the immediate gate is already known.
        Skip if the gate's subtree is inactive (cascade) or the gate's value is
        outside this register's enabling set. If the gate is missing/unreadable,
        read anyway (safe fallback).
        """
        if not reg.gate:
            return True
        gate_key = self._syn2key.get(reg.gate)
        if gate_key is None:
            return True  # gate not loaded -> cannot evaluate
        if gate_active.get(gate_key) is False:
            return False  # an ancestor master is absent -> cascade skip
        value = data.get(gate_key)
        if not isinstance(value, (int, float)):
            return True  # gate unreadable / not numeric -> don't skip
        return int(round(value)) in reg.gate_values

    def _decode_register(self, reg: RegisterDef, raw: list[int]):
        if reg.encoding in ("tprog", "wprog"):
            return decode_schedule(raw, reg.encoding)
        value = decode(raw, reg.encoding, WORD_ORDER_BIG)
        if value is None:
            return None
        if reg.encoding in ("int16", "int32") and reg.scale != 1:
            return round(value * reg.scale, 4)
        if reg.encoding == "float32":
            return round(value, 3)
        return value

    async def async_write(self, reg: RegisterDef, raw_value: int) -> None:
        """Write a single register (FC6), then refresh."""
        await self.hub.write_register(reg.address, raw_value)
        await self._refresh_after_write()

    async def async_write_schedule(self, reg: RegisterDef, words: list[int]) -> None:
        """Write a multi-register schedule (FC16), then refresh."""
        await self.hub.write_registers(reg.address, words)
        await self._refresh_after_write()

    async def _refresh_after_write(self) -> None:
        """Refresh now and again shortly after, since the controller needs a few
        seconds to reflect a written value."""
        await self.async_request_refresh()

        async def _delayed_refresh(_now) -> None:
            await self.async_request_refresh()

        async_call_later(self.hass, WRITE_REFRESH_DELAY, _delayed_refresh)
