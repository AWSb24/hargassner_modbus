"""Binary sensor platform: DAQ-DIG digital read channels."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HargassnerCoordinator
from .entity import HargassnerEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HargassnerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HargassnerBinarySensor(coordinator, reg)
        for reg in coordinator.registers
        if reg.platform == "binary_sensor" and coordinator.should_create(reg)
    )


class HargassnerBinarySensor(HargassnerEntity, BinarySensorEntity):
    """A digital read-only channel."""

    @property
    def is_on(self) -> bool | None:
        value = self._value
        return None if value is None else bool(value)
