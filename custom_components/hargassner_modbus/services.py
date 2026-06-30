"""Services for the Hargassner Modbus integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .const import DOMAIN
from .modbus_hub import ModbusError, encode_schedule

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_SCHEDULE = "set_schedule"
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

SET_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Optional("start_1"): cv.string,
        vol.Optional("stop_1"): cv.string,
        vol.Optional("start_2"): cv.string,
        vol.Optional("stop_2"): cv.string,
        vol.Optional("days"): vol.All(cv.ensure_list, [vol.In(WEEKDAYS)]),
    }
)


def _resolve(hass: HomeAssistant, entity_id: str):
    """Return (coordinator, reg) for a schedule entity, or raise."""
    ent_reg = er.async_get(hass)
    entry = ent_reg.async_get(entity_id)
    if entry is None or entry.platform != DOMAIN:
        raise HomeAssistantError(f"{entity_id} is not a Hargassner Modbus entity")
    coordinator = hass.data.get(DOMAIN, {}).get(entry.config_entry_id)
    if coordinator is None:
        raise HomeAssistantError(f"{entity_id}: integration not loaded")
    key = entry.unique_id[len(entry.config_entry_id) + 1:]
    reg = coordinator.reg_by_key.get(key)
    if reg is None or reg.encoding not in ("tprog", "wprog"):
        raise HomeAssistantError(f"{entity_id} is not a schedule (Tages-/Wochenuhr)")
    return coordinator, reg


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services (once)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        return

    async def handle_set_schedule(call: ServiceCall) -> None:
        data = call.data
        for entity_id in data["entity_id"]:
            coordinator, reg = _resolve(hass, entity_id)
            current = coordinator.data.get(reg.key) or {}
            try:
                words = encode_schedule(
                    reg.encoding,
                    start_1=data.get("start_1", current.get("start_1")),
                    stop_1=data.get("stop_1", current.get("stop_1")),
                    start_2=data.get("start_2", current.get("start_2")),
                    stop_2=data.get("stop_2", current.get("stop_2")),
                    days=data.get("days"),
                    days_mask=None if "days" in data else current.get("days_mask"),
                )
            except ValueError as err:
                raise HomeAssistantError(str(err)) from err
            try:
                await coordinator.async_write_schedule(reg, words)
            except ModbusError as err:
                raise HomeAssistantError(
                    f"{entity_id}: write failed ({err})"
                ) from err
            _LOGGER.debug("Set schedule %s (%s) -> %s", entity_id, reg.address, words)

    hass.services.async_register(
        DOMAIN, SERVICE_SET_SCHEDULE, handle_set_schedule, schema=SET_SCHEDULE_SCHEMA
    )


def async_unload_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SET_SCHEDULE):
        hass.services.async_remove(DOMAIN, SERVICE_SET_SCHEDULE)
