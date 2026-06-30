"""Select platform: the writable WAHL registers (FC6)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
        HargassnerSelect(coordinator, reg)
        for reg in coordinator.registers
        if reg.platform == "select" and coordinator.should_create(reg)
    )


class HargassnerSelect(HargassnerEntity, SelectEntity):
    """A writable enum register exposed as a dropdown."""

    def __init__(self, coordinator: HargassnerCoordinator, reg: RegisterDef) -> None:
        super().__init__(coordinator, reg)
        self._attr_options = list(reg.options.values())

    @property
    def current_option(self) -> str | None:
        value = self._value
        if value is None:
            return None
        return self.reg.options.get(int(value))

    async def async_select_option(self, option: str) -> None:
        index = self.reg.options_by_label.get(option)
        if index is None:
            raise ValueError(f"Unknown option {option!r} for {self.reg.key}")
        # The enum index is the *scaled* state value; convert back to the raw
        # register value. DAQ-ANA (e.g. Programmwahlschalter, scale 0.1) is
        # stored ×10, so index 4 -> raw 40. WAHL (scale 1) stays unchanged.
        raw = round(index / (self.reg.scale or 1))
        await self.coordinator.async_write(self.reg, raw)
