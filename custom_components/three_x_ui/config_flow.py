"""Config flow for 3x-ui Monitor integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import (
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    TIMEOUT_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


async def validate_api(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate connection and credentials against 3x-ui server/status."""
    url = data[CONF_URL].rstrip("/")
    token = data[CONF_TOKEN]
    verify_ssl = data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

    session = async_create_clientsession(hass, verify_ssl=verify_ssl)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    endpoint = f"{url}/panel/api/server/status"

    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            async with session.get(endpoint, headers=headers) as resp:
                if resp.status in (401, 403):
                    raise InvalidAuth
                if resp.status != 200:
                    raise CannotConnect(f"HTTP status {resp.status}")
                payload = await resp.json()
                if not payload.get("success"):
                    raise CannotConnect(payload.get("msg", "Unknown API error"))
                return payload.get("obj") or {}
    except (TimeoutError, asyncio.TimeoutError) as err:
        raise CannotConnect("Connection timed out") from err
    except aiohttp.ClientError as err:
        raise CannotConnect(f"Network error: {err}") from err


class ThreeXUIConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for 3x-ui."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Normalize URL
            raw_url = user_input[CONF_URL].strip().rstrip("/")
            if not raw_url.startswith(("http://", "https://")):
                raw_url = f"http://{raw_url}"
            user_input[CONF_URL] = raw_url

            unique_id = raw_url.lower()
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                await validate_api(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception during config validation")
                errors["base"] = "unknown"
            else:
                title = user_input.get(CONF_NAME, DEFAULT_NAME)
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Required(
                    CONF_URL, default="http://192.168.1.100:2053"
                ): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.URL)
                ),
                vol.Required(CONF_TOKEN): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD
                    )
                ),
                vol.Optional(
                    CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=3600,
                        step=5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return ThreeXUIOptionsFlowHandler(config_entry)


class ThreeXUIOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for 3x-ui."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        current_verify_ssl = self.config_entry.options.get(
            CONF_VERIFY_SSL,
            self.config_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_interval
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5,
                        max=3600,
                        step=5,
                        unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    CONF_VERIFY_SSL, default=current_verify_ssl
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
