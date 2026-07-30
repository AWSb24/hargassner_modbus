"""Constants for the Hargassner Modbus integration."""
from __future__ import annotations

DOMAIN = "hargassner_modbus"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE = "slave"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_ENABLED_CATEGORIES = "enabled_categories"
CONF_EXCLUDED_KEYS = "excluded_keys"
CONF_CUSTOMIZE_ENTITIES = "customize_entities"
CONF_PRESET = "preset"
CONF_GATE_FILTER = "gate_filter"
CONF_REQUEST_DELAY = "request_delay"  # milliseconds between single Modbus reads

# Config-flow presets (step 2).
PRESET_AUTO = "auto"          # all categories, only installed components (gate-filtered)
PRESET_BASIS = "basis"        # core only
PRESET_FULL = "full"          # everything, incl. not-installed (no gate filter)
PRESET_CUSTOM = "custom"      # pick categories / entities manually
PRESETS = [PRESET_AUTO, PRESET_BASIS, PRESET_FULL, PRESET_CUSTOM]

DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN_INTERVAL = 30  # seconds
DEFAULT_REQUEST_DELAY = 0  # milliseconds between single reads (0 = back-to-back)
WRITE_REFRESH_DELAY = 10  # seconds; re-read after a write so the new state shows quickly

PLATFORMS = ["sensor", "binary_sensor", "select", "number"]

# FLOAT / INT32 word order. The Hargassner manual does not state endianness;
# assumed high word first (big-endian word order). Flip to False after a live
# read if 32-bit values look wrong. See memory float-word-order-unverified.
WORD_ORDER_BIG = True

# Modbus function codes
FC_READ_HOLDING = 3
FC_WRITE_SINGLE = 6

# Core categories for the "Basis" preset (and the default pre-selection in the
# custom step). Other categories are added per preset or by the user.
BASIS_CATEGORIES: set[str] = {
    "kessel",
    "zentralpuffer",
    "witterung",
}
