"""Data update coordinator for Steinway Lyngdorf."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .steinway_p100 import SteinwayP100Device, PowerState
from .steinway_p100.exceptions import ConnectionError, TimeoutError
from .zman_sdk import ZMANClient
from .const import CONF_ZMAN_HOST, ZMAN_PORT

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=5)
UPDATE_INTERVAL_FAST = timedelta(seconds=1)
FAST_POLL_COUNT = 10  # 10 fast polls after power on


class SteinwayLyngdorfCoordinator(DataUpdateCoordinator):
    """Coordinator to manage Steinway Lyngdorf data updates and connection."""
    
    def __init__(
        self,
        hass: HomeAssistant,
        device: SteinwayP100Device,
        host: str,
        port: int,
        zman_host: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Steinway Lyngdorf {host}",
            update_interval=UPDATE_INTERVAL,
        )
        self.device = device
        self._host = host
        self._port = port
        self._zman_host = zman_host or host
        self._reconnect_task: asyncio.Task | None = None
        self._available = True
        self._zman: ZMANClient | None = None
        self.current_aes67_stream: str | None = None
        self._last_power_state: PowerState | None = None
        self._fast_polls_remaining = 0
    
    @property
    def available(self) -> bool:
        """Return if the device is available."""
        return self._available and self.device.is_connected
    
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device."""
        if not self.device.is_connected:
            # Try to reconnect
            if self._reconnect_task is None or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect())
            raise UpdateFailed("Device not connected")
        
        try:
            # Get basic status
            data = {
                "power_state": await self.device.power.status(),
                "zone2_power_state": await self.device.zone2_power.status(),
            }
            
            # Detect power-on transition → fast polling
            power = data["power_state"]
            if power == PowerState.ON and self._last_power_state != PowerState.ON:
                self._fast_polls_remaining = FAST_POLL_COUNT
                self.update_interval = UPDATE_INTERVAL_FAST
                _LOGGER.debug("Power on detected, switching to fast polling")
            self._last_power_state = power

            if self._fast_polls_remaining > 0:
                self._fast_polls_remaining -= 1
                if self._fast_polls_remaining == 0:
                    self.update_interval = UPDATE_INTERVAL
                    _LOGGER.debug("Fast polling complete, back to %ss", UPDATE_INTERVAL.total_seconds())

            # Get additional data if powered on
            if data["power_state"] == PowerState.ON:
                try:
                    # Volume
                    data["volume"] = await self.device.volume.get()
                    
                    # Mute status - The P100 doesn't reliably respond to MUTE?
                    # so we don't query it to avoid timeouts
                    data["is_muted"] = False
                    
                    # Source
                    current_source = await self.device.source.get_current()
                    data["source_name"] = current_source.name
                    data["source_index"] = current_source.index
                    
                    # Audio mode
                    current_mode = await self.device.audio_mode.get_current()
                    data["audio_mode"] = current_mode.name
                    data["audio_mode_index"] = current_mode.index
                    
                    # Audio type
                    data["audio_type"] = await self.device.audio_mode.get_audio_type()
                    
                    # Media information if available
                    if self.device.media:
                        try:
                            media_info = await self.device.media.get_media_info()
                            data["media_info"] = media_info
                        except Exception as err:
                            _LOGGER.debug("Error fetching media info: %s", err)

                    # AES67 stream detection via ZMAN sinks (discovery only)
                    if "aes67" not in data.get("source_name", "").lower():
                        self.current_aes67_stream = None
                    elif self.current_aes67_stream is None:
                        # No stream set (startup/recovery) — discover from sinks
                        try:
                            zman = await self.async_get_zman()
                            sinks = await self.hass.async_add_executor_job(zman.get_sinks)
                            for sink in sinks:
                                src = sink.get("source", "")
                                if src.startswith("sap://") and sink.get("state_code", 0) >= 2:
                                    self.current_aes67_stream = src
                                    break
                        except Exception as err:
                            _LOGGER.debug("Error fetching ZMAN sinks: %s", err)

                except Exception as err:
                    _LOGGER.debug("Error fetching extended data: %s", err)
            
            self._available = True
            return data
            
        except (ConnectionError, TimeoutError) as err:
            self._available = False
            # Trigger reconnection
            if self._reconnect_task is None or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(self._reconnect())
            raise UpdateFailed(f"Error communicating with device: {err}")
        except Exception as err:
            _LOGGER.exception("Unexpected error updating data")
            raise UpdateFailed(f"Unexpected error: {err}")
    
    async def _reconnect(self) -> None:
        """Try to reconnect to the device."""
        _LOGGER.info("Attempting to reconnect to %s:%s", self._host, self._port)
        
        retry_count = 0
        while retry_count < 3:
            try:
                # Disconnect first if connected
                if self.device.is_connected:
                    await self.device.disconnect()
                
                # Try to reconnect
                await self.device.connect()
                _LOGGER.info("Successfully reconnected to %s:%s", self._host, self._port)
                self._available = True
                
                # Force an update
                await self.async_request_refresh()
                return
                
            except Exception as err:
                retry_count += 1
                _LOGGER.warning(
                    "Reconnection attempt %s/3 failed: %s",
                    retry_count,
                    err
                )
                if retry_count < 3:
                    await asyncio.sleep(10 * retry_count)  # Exponential backoff
        
        _LOGGER.error("Failed to reconnect after 3 attempts")
        self._available = False
    
    async def async_set_audio_mode(self, mode_index: int | None = None, mode_name: str | None = None) -> None:
        """Set audio processing mode."""
        if not self.available:
            raise Exception("Device not available")
        
        try:
            if mode_index is not None:
                await self.device.audio_mode.select(mode_index)
            elif mode_name is not None:
                await self.device.audio_mode.select_by_name(mode_name)
            else:
                raise ValueError("Either mode_index or mode_name must be provided")
            
            # Refresh data
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set audio mode: %s", err)
            raise

    async def async_get_zman(self) -> ZMANClient:
        """Lazily create and connect the ZMAN client."""
        if self._zman is None:
            client = ZMANClient(self._zman_host, ZMAN_PORT)
            await self.hass.async_add_executor_job(client.connect)
            self._zman = client
        return self._zman

    async def async_close_zman(self) -> None:
        """Close the ZMAN client if connected."""
        if self._zman is not None:
            await self.hass.async_add_executor_job(self._zman.close)
            self._zman = None