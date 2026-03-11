"""The Steinway Lyngdorf integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .steinway_p100 import SteinwayP100Device
from .steinway_p100.exceptions import ConnectionError

from .const import CONF_ZMAN_HOST, DOMAIN
from .coordinator import SteinwayLyngdorfCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Steinway Lyngdorf from a config entry."""
    host = entry.data["host"]
    port = entry.data.get("port", 84)
    
    device = SteinwayP100Device.from_tcp(host, port)
    
    try:
        await device.connect()
    except ConnectionError as err:
        raise ConfigEntryNotReady(f"Cannot connect to {host}:{port}") from err
    
    # Create coordinator
    zman_host = entry.data.get(CONF_ZMAN_HOST)
    coordinator = SteinwayLyngdorfCoordinator(hass, device, host, port, zman_host)

    # Register push notification callback for real-time state updates
    device.set_notification_callback(coordinator._handle_notification)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_close_zman()
        await coordinator.device.disconnect()
    
    return unload_ok