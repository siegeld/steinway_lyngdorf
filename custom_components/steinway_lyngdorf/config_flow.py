"""Config flow for Steinway Lyngdorf integration."""
from __future__ import annotations

import logging
import socket
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .steinway_p100 import SteinwayP100Device
from .steinway_p100.exceptions import ConnectionError

from .const import CONF_ZMAN_HOST, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=84): int,
        vol.Optional(CONF_ZMAN_HOST): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Steinway Lyngdorf."""
    
    VERSION = 1
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
            # Test DNS resolution first
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            
            # DNS resolution needs to be done in executor to avoid blocking
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                ip = await loop.run_in_executor(None, socket.gethostbyname, host)
                _LOGGER.debug(f"DNS resolved {host} to {ip}")
            except socket.gaierror as e:
                _LOGGER.error(f"DNS resolution failed for {host}: {e}")
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_DATA_SCHEMA,
                    errors=errors,
                )
            
            # Test the connection
            device = SteinwayP100Device.from_tcp(host, port)
            
            try:
                _LOGGER.debug(f"Attempting to connect to {host}:{port}")
                await device.connect()
                await device.disconnect()
                _LOGGER.debug(f"Successfully connected to {host}:{port}")
            except ConnectionError as e:
                _LOGGER.error(f"Connection error to {host}:{port}: {e}")
                errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.exception(f"Unexpected exception connecting to {host}:{port}: {e}")
                errors["base"] = "unknown"
            else:
                # Connection successful
                await self.async_set_unique_id(f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}")
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"Steinway Lyngdorf {user_input[CONF_HOST]}",
                    data=user_input,
                )
        
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )