"""Base entity for Hargassner Modbus."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HargassnerCoordinator
from .registers import RegisterDef


class HargassnerEntity(CoordinatorEntity[HargassnerCoordinator]):
    """Common base linking an entity to one register."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HargassnerCoordinator, reg: RegisterDef) -> None:
        super().__init__(coordinator)
        self.reg = reg
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{reg.key}"
        self._attr_name = reg.name

    @property
    def device_info(self) -> DeviceInfo:
        entry_id = self.coordinator.config_entry.entry_id
        return DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Hargassner Heizung",
            manufacturer="Hargassner",
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.get(self.reg.key) is not None
            # hidden when a controlling master says the component isn't installed
            and self.coordinator.gate_active.get(self.reg.key, True)
        )

    @property
    def extra_state_attributes(self):
        attrs = {"address": self.reg.address}
        if self.reg.synonym:
            attrs["synonym"] = self.reg.synonym
        if self.reg.gate:
            attrs["gate"] = self.reg.gate
        return attrs

    @property
    def _value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.reg.key)
