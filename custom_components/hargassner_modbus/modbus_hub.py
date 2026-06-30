"""Thin async wrapper around pymodbus for the Hargassner controller."""
from __future__ import annotations

import asyncio
import inspect
import logging
import struct

from pymodbus.client import AsyncModbusTcpClient

_LOGGER = logging.getLogger(__name__)

# pymodbus renamed the unit/slave keyword from "slave" to "device_id" around
# 3.8. Pick whichever the installed version exposes so the integration keeps
# working across Home Assistant upgrades.
try:
    _params = inspect.signature(AsyncModbusTcpClient.read_holding_registers).parameters
    _DEVICE_KW = "device_id" if "device_id" in _params else "slave"
except (ValueError, TypeError):  # pragma: no cover - defensive
    _DEVICE_KW = "slave"


class ModbusError(Exception):
    """Base error for a failed Modbus request."""


class ModbusConnectionError(ModbusError):
    """The TCP connection could not be established or was lost."""


class ModbusDataError(ModbusError):
    """The device replied with an exception response (e.g. illegal address).

    The connection itself is fine; only this particular request is invalid, so
    the caller can skip the affected registers and keep polling the rest.
    """


class HargassnerHub:
    """Manage a single Modbus TCP connection to the heating controller."""

    def __init__(self, host: str, port: int, slave: int) -> None:
        self._host = host
        self._port = port
        self._slave = slave
        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

    async def _ensure_connected(self) -> AsyncModbusTcpClient:
        # The controller drops the TCP connection on some errors, so always
        # recreate a fresh client when we are not connected.
        if self._client is not None and self._client.connected:
            return self._client
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001 - best effort
                pass
        self._client = AsyncModbusTcpClient(self._host, port=self._port)
        try:
            ok = await self._client.connect()
        except Exception as err:  # noqa: BLE001
            self._client = None
            raise ModbusConnectionError(
                f"Cannot connect to {self._host}:{self._port}: {err}"
            ) from err
        if not ok or not self._client.connected:
            self._client = None
            raise ModbusConnectionError(f"Cannot connect to {self._host}:{self._port}")
        return self._client

    async def read_block(self, address: int, count: int) -> list[int]:
        """Read ``count`` holding registers starting at ``address``."""
        async with self._lock:
            client = await self._ensure_connected()
            try:
                rr = await client.read_holding_registers(
                    address, count=count, **{_DEVICE_KW: self._slave}
                )
            except Exception as err:  # noqa: BLE001 - transport/connection lost
                self._client = None
                raise ModbusConnectionError(f"read {address}+{count}: {err}") from err
            if rr.isError():
                raise ModbusDataError(f"read {address}+{count}: {rr}")
            return list(rr.registers)

    async def write_register(self, address: int, value: int) -> None:
        """Write a single holding register (FC6)."""
        async with self._lock:
            client = await self._ensure_connected()
            try:
                rq = await client.write_register(
                    address, value, **{_DEVICE_KW: self._slave}
                )
            except Exception as err:  # noqa: BLE001
                self._client = None
                raise ModbusConnectionError(f"write {address}={value}: {err}") from err
            if rq.isError():
                raise ModbusDataError(f"write {address}={value}: {rq}")

    async def write_registers(self, address: int, values: list[int]) -> None:
        """Write several consecutive holding registers (FC16)."""
        async with self._lock:
            client = await self._ensure_connected()
            try:
                rq = await client.write_registers(
                    address, list(values), **{_DEVICE_KW: self._slave}
                )
            except Exception as err:  # noqa: BLE001
                self._client = None
                raise ModbusConnectionError(
                    f"write {address}={values}: {err}"
                ) from err
            if rq.isError():
                raise ModbusDataError(f"write {address}={values}: {rq}")

    async def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
            self._client = None


# --- value decoding -------------------------------------------------------

def _to_signed16(value: int) -> int:
    return value - 0x10000 if value >= 0x8000 else value


def decode(regs: list[int], encoding: str, word_order_big: bool) -> float | int | bool | None:
    """Decode raw register words into a Python number."""
    if not regs:
        return None
    if encoding == "bool":
        return bool(regs[0])
    if encoding == "int16":
        return _to_signed16(regs[0])
    if encoding in ("int32", "float32"):
        if len(regs) < 2:
            return None
        hi, lo = (regs[0], regs[1]) if word_order_big else (regs[1], regs[0])
        raw = (hi << 16) | lo
        if encoding == "int32":
            if raw >= 0x80000000:
                raw -= 0x100000000
            return raw
        return struct.unpack(">f", struct.pack(">I", raw))[0]
    return _to_signed16(regs[0])


# --- schedule decoding (Tages-/Wochenprogramm) ----------------------------

# Weekday bit -> abbreviation (manual p.5: bit0=Sonntag … bit6=Samstag).
_WEEKDAYS = {0: "So", 1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa"}
_WEEKDAY_ORDER = [1, 2, 3, 4, 5, 6, 0]  # display Monday-first


def _fmt_minutes(value: int | None) -> str | None:
    if value is None:
        return None
    h, m = divmod(int(value), 60)
    return f"{h:02d}:{m:02d}"


def decode_schedule(regs: list[int], kind: str) -> dict | None:
    """Decode a TPROG (4 regs) or WPROG (5 regs) into a structured schedule.

    TPROG: start1, start2, stop1, stop2 (minutes from 00:00).
    WPROG: weekday-bitmask, start1, start2, stop1, stop2.
    A window with start == stop is treated as inactive.
    """
    days_mask = None
    if kind == "wprog":
        if len(regs) < 5:
            return None
        days_mask, start1, start2, stop1, stop2 = regs[:5]
    else:  # tprog
        if len(regs) < 4:
            return None
        start1, start2, stop1, stop2 = regs[:4]

    windows = []
    for start, stop in ((start1, stop1), (start2, stop2)):
        if start != stop:
            windows.append({"start": _fmt_minutes(start), "stop": _fmt_minutes(stop)})

    result: dict = {
        "windows": windows,
        "start_1": _fmt_minutes(start1),
        "stop_1": _fmt_minutes(stop1),
        "start_2": _fmt_minutes(start2),
        "stop_2": _fmt_minutes(stop2),
    }
    if days_mask is not None:
        result["days"] = [
            _WEEKDAYS[b] for b in _WEEKDAY_ORDER if days_mask & (1 << b)
        ]
        result["days_mask"] = days_mask
    return result


def schedule_summary(data: dict | None) -> str | None:
    """One-line summary of a decoded schedule, e.g. 'Mo, Di: 06:00–22:00'."""
    if data is None:
        return None
    windows = data.get("windows")
    win_txt = (
        ", ".join(f'{w["start"]}–{w["stop"]}' for w in windows)
        if windows
        else "Aus"
    )
    days = data.get("days")
    if days:
        return f"{', '.join(days)}: {win_txt}"
    return win_txt


# --- schedule encoding (for writing back via FC16) ------------------------

_WEEKDAY_BIT = {abbr: bit for bit, abbr in _WEEKDAYS.items()}


def parse_minutes(value) -> int:
    """Accept 'HH:MM[:SS]' or a number of minutes and return minutes (0..1440)."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if ":" in s:
        parts = s.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    return int(s)


def days_to_mask(days) -> int:
    mask = 0
    for d in days or []:
        bit = _WEEKDAY_BIT.get(d)
        if bit is not None:
            mask |= 1 << bit
    return mask


def encode_schedule(kind: str, *, start_1, stop_1, start_2, stop_2,
                    days=None, days_mask=None) -> list[int]:
    """Build the raw register words for a TPROG/WPROG schedule.

    Times are minutes from 00:00 (0..1440). Raises ValueError on out-of-range.
    """
    s1, e1 = parse_minutes(start_1), parse_minutes(stop_1)
    s2, e2 = parse_minutes(start_2), parse_minutes(stop_2)
    for t in (s1, e1, s2, e2):
        if not 0 <= t <= 1440:
            raise ValueError(f"time {t} out of range (0..1440 minutes)")
    if kind == "wprog":
        mask = days_mask if days_mask is not None else days_to_mask(days)
        return [mask & 0x7F, s1, s2, e1, e2]
    return [s1, s2, e1, e2]
