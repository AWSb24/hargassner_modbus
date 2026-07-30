"""The Hargassner Modbus integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_ENABLED_CATEGORIES,
    CONF_EXCLUDED_KEYS,
    CONF_HOST,
    CONF_PORT,
    CONF_PRESET,
    CONF_REQUEST_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
    PLATFORMS,
    PRESET_AUTO,
    PRESET_BASIS,
    PRESET_CUSTOM,
    PRESET_FULL,
)
from .coordinator import HargassnerCoordinator
from .modbus_hub import HargassnerHub
from .registers import (
    active_registers,
    all_categories_registers,
    basis_registers,
)
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)


def select_registers(options):
    """Return (registers, gate_filter) for the chosen preset."""
    preset = options.get(CONF_PRESET, PRESET_CUSTOM)
    if preset == PRESET_BASIS:
        return basis_registers(), True
    if preset in (PRESET_AUTO, PRESET_FULL):
        return all_categories_registers(), preset == PRESET_AUTO
    # custom (also the default for entries created before presets existed)
    regs = active_registers(
        set(options.get(CONF_ENABLED_CATEGORIES, [])),
        set(options.get(CONF_EXCLUDED_KEYS, [])),
    )
    return regs, True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hargassner Modbus from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave = entry.data.get(CONF_SLAVE, DEFAULT_SLAVE)

    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    request_delay = entry.options.get(CONF_REQUEST_DELAY, DEFAULT_REQUEST_DELAY) / 1000
    registers, gate_filter = await hass.async_add_executor_job(
        select_registers, entry.options
    )

    hub = HargassnerHub(host, port, slave)

    coordinator = HargassnerCoordinator(
        hass, entry, hub, registers, scan_interval, gate_filter, request_delay
    )
    # First refresh populates gate_active, which decides which entities to create.
    await coordinator.async_config_entry_first_refresh()

    # Keep only entities that will actually be created (selection + gate filter);
    # remove the rest so deselected / not-installed ones don't linger.
    create = [r for r in registers if coordinator.should_create(r)]
    _async_cleanup_entities(hass, entry, create)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


def _async_cleanup_entities(hass, entry, registers) -> None:
    """Drop registry entries whose register is no longer created."""
    valid_unique_ids = {f"{entry.entry_id}_{reg.key}" for reg in registers}
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id not in valid_unique_ids:
            _LOGGER.debug("Removing entity %s", entity.entity_id)
            registry.async_remove(entity.entity_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: HargassnerCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.hub.close()
        if not hass.data[DOMAIN]:  # last entry -> drop the service
            async_unload_services(hass)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
