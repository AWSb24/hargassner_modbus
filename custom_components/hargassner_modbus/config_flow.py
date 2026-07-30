"""Config and options flow for Hargassner Modbus.

Config flow:
  1. user    -> network data (host / port / slave), with a connection test
  2. preset  -> Automatisch / Basis / Komplett / Benutzerdefiniert
  3. categories / entities  -> only for the "Benutzerdefiniert" preset

The options flow mirrors steps 2/3 and additionally exposes the scan interval.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    BASIS_CATEGORIES,
    CONF_CUSTOMIZE_ENTITIES,
    CONF_ENABLED_CATEGORIES,
    CONF_EXCLUDED_KEYS,
    CONF_HOST,
    CONF_PORT,
    CONF_PRESET,
    CONF_REQUEST_DELAY,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_PORT,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
    PRESET_AUTO,
    PRESET_BASIS,
    PRESET_CUSTOM,
    PRESET_FULL,
)
from .modbus_hub import HargassnerHub, ModbusError
from .registers import categories, registers_in_categories

_PRESET_LABELS = {
    PRESET_AUTO: "Automatisch – nur tatsächlich vorhandene Komponenten",
    PRESET_BASIS: "Basis – Kessel, Zentralpuffer, Witterung",
    PRESET_FULL: "Komplett – alle Register (auch nicht vorhandene)",
    PRESET_CUSTOM: "Benutzerdefiniert – Kategorien/Entitäten selbst wählen",
}


async def _test_connection(host: str, port: int, slave: int) -> None:
    hub = HargassnerHub(host, port, slave)
    try:
        # Programmwahlschalter (11336) exists on every controller.
        await hub.read_block(11336, 1)
    finally:
        await hub.close()


def _preset_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=p, label=_PRESET_LABELS[p])
                for p in (PRESET_AUTO, PRESET_BASIS, PRESET_FULL, PRESET_CUSTOM)
            ],
            mode=SelectSelectorMode.LIST,
        )
    )


def _category_selector() -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=[
                SelectOptionDict(value=c, label=c.replace("_", " ").title())
                for c in categories()
            ],
            multiple=True,
            mode=SelectSelectorMode.LIST,
        )
    )


def _entity_options(enabled_categories: list[str]) -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=reg.key, label=reg.name)
        for reg in registers_in_categories(set(enabled_categories))
    ]


def _entity_selector(enabled_categories: list[str]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=_entity_options(enabled_categories),
            multiple=True,
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


class HargassnerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Initial configuration: network data, then a preset (or custom selection)."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._categories: list[str] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            slave = user_input[CONF_SLAVE]
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()
            try:
                await _test_connection(host, port, slave)
            except ModbusError:
                errors["base"] = "cannot_connect"
            else:
                self._data = user_input
                return await self.async_step_preset()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_preset(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            preset = user_input[CONF_PRESET]
            if preset == PRESET_CUSTOM:
                return await self.async_step_categories()
            return self.async_create_entry(
                title=f"Hargassner ({self._data[CONF_HOST]})",
                data=self._data,
                options={CONF_PRESET: preset},
            )

        schema = vol.Schema({vol.Required(CONF_PRESET, default=PRESET_AUTO): _preset_selector()})
        return self.async_show_form(step_id="preset", data_schema=schema)

    async def async_step_categories(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._categories = user_input[CONF_ENABLED_CATEGORIES]
            if user_input.get(CONF_CUSTOMIZE_ENTITIES) and self._categories:
                return await self.async_step_entities()
            return self.async_create_entry(
                title=f"Hargassner ({self._data[CONF_HOST]})",
                data=self._data,
                options={
                    CONF_PRESET: PRESET_CUSTOM,
                    CONF_ENABLED_CATEGORIES: self._categories,
                    CONF_EXCLUDED_KEYS: [],
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLED_CATEGORIES,
                    default=sorted(BASIS_CATEGORIES & set(categories())),
                ): _category_selector(),
                vol.Optional(CONF_CUSTOMIZE_ENTITIES, default=False): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="categories", data_schema=schema)

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        all_keys = [o["value"] for o in _entity_options(self._categories)]
        if user_input is not None:
            selected = set(user_input.get("entities", []))
            excluded = [k for k in all_keys if k not in selected]
            return self.async_create_entry(
                title=f"Hargassner ({self._data[CONF_HOST]})",
                data=self._data,
                options={
                    CONF_PRESET: PRESET_CUSTOM,
                    CONF_ENABLED_CATEGORIES: self._categories,
                    CONF_EXCLUDED_KEYS: excluded,
                },
            )

        schema = vol.Schema(
            {
                vol.Optional("entities", default=all_keys): _entity_selector(
                    self._categories
                ),
            }
        )
        return self.async_show_form(step_id="entities", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HargassnerOptionsFlow()


class HargassnerOptionsFlow(OptionsFlow):
    """Adjust preset / scan interval, and (for custom) categories + entities."""

    def __init__(self) -> None:
        self._scan_interval = DEFAULT_SCAN_INTERVAL
        self._request_delay = DEFAULT_REQUEST_DELAY
        self._categories: list[str] = []

    def _base_options(self) -> dict[str, Any]:
        return {
            CONF_SCAN_INTERVAL: self._scan_interval,
            CONF_REQUEST_DELAY: self._request_delay,
        }

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        opts = self.config_entry.options
        if user_input is not None:
            self._scan_interval = user_input[CONF_SCAN_INTERVAL]
            self._request_delay = user_input[CONF_REQUEST_DELAY]
            preset = user_input[CONF_PRESET]
            if preset == PRESET_CUSTOM:
                return await self.async_step_categories()
            return self.async_create_entry(
                title="", data={CONF_PRESET: preset, **self._base_options()}
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_PRESET, default=opts.get(CONF_PRESET, PRESET_CUSTOM)
                ): _preset_selector(),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(int, vol.Range(min=5, max=3600)),
                vol.Required(
                    CONF_REQUEST_DELAY,
                    default=opts.get(CONF_REQUEST_DELAY, DEFAULT_REQUEST_DELAY),
                ): vol.All(int, vol.Range(min=0, max=1000)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_categories(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        opts = self.config_entry.options
        valid = categories()
        if user_input is not None:
            self._categories = user_input[CONF_ENABLED_CATEGORIES]
            if user_input.get(CONF_CUSTOMIZE_ENTITIES) and self._categories:
                return await self.async_step_entities()
            return self.async_create_entry(
                title="",
                data={
                    CONF_PRESET: PRESET_CUSTOM,
                    CONF_ENABLED_CATEGORIES: self._categories,
                    CONF_EXCLUDED_KEYS: [],
                    **self._base_options(),
                },
            )

        selected = [c for c in opts.get(CONF_ENABLED_CATEGORIES, []) if c in valid]
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENABLED_CATEGORIES, default=selected
                ): _category_selector(),
                vol.Optional(CONF_CUSTOMIZE_ENTITIES, default=False): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="categories", data_schema=schema)

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        all_keys = [o["value"] for o in _entity_options(self._categories)]
        if user_input is not None:
            selected = set(user_input.get("entities", []))
            excluded = [k for k in all_keys if k not in selected]
            return self.async_create_entry(
                title="",
                data={
                    CONF_PRESET: PRESET_CUSTOM,
                    CONF_ENABLED_CATEGORIES: self._categories,
                    CONF_EXCLUDED_KEYS: excluded,
                    **self._base_options(),
                },
            )

        previously_excluded = set(self.config_entry.options.get(CONF_EXCLUDED_KEYS, []))
        default_selected = [k for k in all_keys if k not in previously_excluded]
        schema = vol.Schema(
            {
                vol.Optional("entities", default=default_selected): _entity_selector(
                    self._categories
                ),
            }
        )
        return self.async_show_form(step_id="entities", data_schema=schema)
