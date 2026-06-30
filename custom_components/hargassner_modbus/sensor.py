"""Sensor platform: read-only numeric and enum/state registers."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HargassnerCoordinator
from .entity import HargassnerEntity
from .modbus_hub import schedule_summary
from .registers import RegisterDef


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: HargassnerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        HargassnerSensor(coordinator, reg)
        for reg in coordinator.registers
        if reg.platform == "sensor" and coordinator.should_create(reg)
    )


class HargassnerSensor(HargassnerEntity, SensorEntity):
    """A read-only Hargassner register."""

    def __init__(self, coordinator: HargassnerCoordinator, reg: RegisterDef) -> None:
        super().__init__(coordinator, reg)
        self._is_schedule = reg.encoding in ("tprog", "wprog")
        if self._is_schedule:
            self._attr_icon = "mdi:calendar-clock"
        elif reg.options:
            # enum/state register -> textual state, no unit/device_class
            self._attr_device_class = "enum"
            self._attr_options = list(reg.options.values())
        else:
            self._attr_native_unit_of_measurement = reg.unit
            self._attr_device_class = reg.device_class
            self._attr_state_class = reg.state_class

    @property
    def native_value(self):
        value = self._value
        if value is None:
            return None
        if self._is_schedule:
            return schedule_summary(value)
        if self.reg.options:
            return self.reg.options.get(int(value))
        return value

    @property
    def extra_state_attributes(self):
        attrs = dict(super().extra_state_attributes or {})
        if self._is_schedule and isinstance(self._value, dict):
            data = self._value
            attrs.update(
                start_1=data.get("start_1"),
                stop_1=data.get("stop_1"),
                start_2=data.get("start_2"),
                stop_2=data.get("stop_2"),
            )
            if "days" in data:
                attrs["days"] = data["days"]
        return attrs
