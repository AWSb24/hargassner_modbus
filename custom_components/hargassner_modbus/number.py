"""Number platform: writable numeric registers (FC6, non-enum).

Currently every writable register in the curated set is an enum (handled by the
select platform), so this platform usually creates no entities. It exists so that
future writable numeric registers work without code changes.
"""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HargassnerCoordinator
from .entity import HargassnerEntity
from .registers import RegisterDef


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HargassnerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HargassnerNumber(coordinator, reg)
        for reg in coordinator.registers
        if reg.platform == "number" and coordinator.should_create(reg)
    )


class HargassnerNumber(HargassnerEntity, NumberEntity):
    """A writable numeric register."""

    def __init__(self, coordinator: HargassnerCoordinator, reg: RegisterDef) -> None:
        super().__init__(coordinator, reg)
        self._attr_native_unit_of_measurement = reg.unit
        self._attr_device_class = reg.device_class
        if reg.min is not None:
            self._attr_native_min_value = reg.min
        if reg.max is not None:
            self._attr_native_max_value = reg.max
        if reg.step is not None:
            self._attr_native_step = reg.step

    @property
    def native_value(self) -> float | None:
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        raw = round(value / (self.reg.scale or 1))
        await self.coordinator.async_write(self.reg, int(raw))
