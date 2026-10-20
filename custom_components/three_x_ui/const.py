"""Constants for the 3x-ui Monitor integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "three_x_ui"

CONF_NAME = "name"
CONF_URL = "url"
CONF_TOKEN = "token"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "3x-ui Server"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_VERIFY_SSL = False
TIMEOUT_SECONDS = 10

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]
