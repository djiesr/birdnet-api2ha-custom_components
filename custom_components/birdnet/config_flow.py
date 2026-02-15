"""Config flow for BirdNET (birdnet-api2ha)."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_STATION_NAME,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_TIMEOUT,
    CONF_STATION_NAME,
    CONF_UPDATE_INTERVAL,
    CONF_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STATION_NAME, default=DEFAULT_STATION_NAME): str,
        vol.Required(CONF_HOST, default="192.168.1.1"): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=600)
        ),
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=60)
        ),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input by connecting to the API."""
    host = data[CONF_HOST].strip()
    port = data[CONF_PORT]
    timeout = aiohttp.ClientTimeout(total=data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
    base_url = f"http://{host}:{port}"

    try:
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            for url in (f"{base_url}/health", f"{base_url}/api/stats"):
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            station = (data.get(CONF_STATION_NAME) or DEFAULT_STATION_NAME).strip() or DEFAULT_STATION_NAME
                            return {"title": f"BirdNET {station} ({host}:{port})"}
                except (aiohttp.ClientError, TimeoutError):
                    continue
        raise CannotConnect
    except CannotConnect:
        raise
    except Exception as err:
        _LOGGER.exception("Unexpected error: %s", err)
        raise CannotConnect from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BirdNET."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect to the API."""
