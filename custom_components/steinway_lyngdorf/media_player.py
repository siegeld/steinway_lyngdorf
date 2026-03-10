"""Media player platform for Steinway Lyngdorf."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.media_player import (
    BrowseError,
    BrowseMedia,
    MediaClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .steinway_p100 import PowerState
from .steinway_p100.api.models import PlaybackState
from .steinway_p100.exceptions import CommandError

from .const import (
    ATTR_AUDIO_MODE,
    ATTR_AUDIO_MODES,
    ATTR_AUDIO_TYPE,
    ATTR_DELAY_MS,
    ATTR_MODE_INDEX,
    ATTR_MODE_NAME,
    ATTR_POSITION_INDEX,
    ATTR_POSITION_NAME,
    DOMAIN,
    MEDIA_TYPE_AES67,
    SERVICE_SET_AUDIO_MODE,
    SERVICE_SET_LIPSYNC,
    SERVICE_SET_ROOM_PERFECT,
)
from .coordinator import SteinwayLyngdorfCoordinator

_LOGGER = logging.getLogger(__name__)

# Conversion factor for Home Assistant volume (0-1) to device volume (dB)
MIN_VOLUME_DB = -60.0  # Practical minimum for UI
MAX_VOLUME_DB = 0.0    # Maximum volume


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Steinway Lyngdorf media player from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    media_player = SteinwayLyngdorfMediaPlayer(coordinator, config_entry)
    async_add_entities([media_player])
    
    # Register services
    platform = async_get_current_platform()
    
    platform.async_register_entity_service(
        SERVICE_SET_AUDIO_MODE,
        {
            vol.Optional(ATTR_MODE_INDEX): cv.positive_int,
            vol.Optional(ATTR_MODE_NAME): cv.string,
        },
        "async_set_audio_mode",
    )
    
    platform.async_register_entity_service(
        SERVICE_SET_ROOM_PERFECT,
        {
            vol.Optional(ATTR_POSITION_INDEX): cv.positive_int,
            vol.Optional(ATTR_POSITION_NAME): cv.string,
        },
        "async_set_room_perfect",
    )
    
    platform.async_register_entity_service(
        SERVICE_SET_LIPSYNC,
        {
            vol.Required(ATTR_DELAY_MS): vol.Coerce(int),
        },
        "async_set_lipsync",
    )


class SteinwayLyngdorfMediaPlayer(CoordinatorEntity[SteinwayLyngdorfCoordinator], MediaPlayerEntity):
    """Representation of a Steinway Lyngdorf media player."""
    
    _attr_has_entity_name = True
    _attr_name = None
    
    def __init__(self, coordinator: SteinwayLyngdorfCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize the media player."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_media_player"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": f"Steinway Lyngdorf {config_entry.data['host']}",
            "manufacturer": "Steinway Lyngdorf",
            "model": "P100/P200/P300",
        }
        
        self._attr_supported_features = (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.BROWSE_MEDIA
            | MediaPlayerEntityFeature.PLAY_MEDIA
        )
        
        # Add media control features if media API is available
        if coordinator.device.media:
            self._attr_supported_features |= (
                MediaPlayerEntityFeature.PLAY
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.NEXT_TRACK
                | MediaPlayerEntityFeature.PREVIOUS_TRACK
            )
        
        self._source_list: list[str] = []
        self._audio_modes: list[str] = []
        self._is_muted: bool = False  # Track mute state locally
        
    async def async_added_to_hass(self) -> None:
        """Run when entity is added to hass."""
        await super().async_added_to_hass()
        
        # Load available sources and audio modes
        try:
            sources = await self.coordinator.device.source.get_sources()
            self._source_list = [source.name for source in sources]
            
            modes = await self.coordinator.device.audio_mode.get_modes()
            self._audio_modes = [mode.name for mode in modes]
        except Exception:
            _LOGGER.exception("Failed to load sources or audio modes")
    
    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.available
    
    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the device."""
        if not self.coordinator.data:
            return MediaPlayerState.OFF
            
        power_state = self.coordinator.data.get("power_state", PowerState.OFF)
        if power_state == PowerState.OFF:
            return MediaPlayerState.OFF
        
        # Check media playback state if available
        media_info = self.coordinator.data.get("media_info")
        if media_info:
            if media_info.state == PlaybackState.PLAYING:
                return MediaPlayerState.PLAYING
            elif media_info.state == PlaybackState.PAUSED:
                return MediaPlayerState.PAUSED
        
        return MediaPlayerState.IDLE
    
    @property
    def volume_level(self) -> float | None:
        """Return the volume level."""
        if not self.coordinator.data or "volume" not in self.coordinator.data:
            return None
            
        volume_db = self.coordinator.data["volume"]
        return self._db_to_level(volume_db)
    
    @property
    def is_volume_muted(self) -> bool:
        """Return true if volume is muted."""
        # P100 doesn't report mute status reliably, so we track it locally
        return self._is_muted
    
    @property
    def source(self) -> str | None:
        """Return the current input source."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("source_name")
    
    @property
    def source_list(self) -> list[str]:
        """Return the list of available input sources."""
        return self._source_list
    
    @property
    def media_title(self) -> str | None:
        """Return the title of current playing media."""
        if not self.coordinator.data:
            return None
        media_info = self.coordinator.data.get("media_info")
        return media_info.title if media_info else None
    
    @property
    def media_artist(self) -> str | None:
        """Return the artist of current playing media."""
        if not self.coordinator.data:
            return None
        media_info = self.coordinator.data.get("media_info")
        return media_info.artist if media_info else None
    
    @property
    def media_album_name(self) -> str | None:
        """Return the album name of current playing media."""
        if not self.coordinator.data:
            return None
        media_info = self.coordinator.data.get("media_info")
        return media_info.album if media_info else None
    
    @property
    def media_position(self) -> int | None:
        """Position of current playing media in seconds."""
        if not self.coordinator.data:
            return None
        media_info = self.coordinator.data.get("media_info")
        if media_info and media_info.position_ms:
            return media_info.position_ms // 1000
        return None
    
    @property
    def media_duration(self) -> int | None:
        """Duration of current playing media in seconds."""
        if not self.coordinator.data:
            return None
        media_info = self.coordinator.data.get("media_info")
        if media_info and media_info.duration_ms:
            return media_info.duration_ms // 1000
        return None
    
    @property
    def media_content_id(self) -> str | None:
        """Content ID of current playing media."""
        if not self.coordinator.data:
            return None
        media_info = self.coordinator.data.get("media_info")
        if media_info and (media_info.title or media_info.artist):
            # Return something to indicate media is present
            return f"{media_info.service or 'steinway'}:{media_info.title or 'Unknown'}"
        return None
    
    @property
    def media_content_type(self) -> str | None:
        """Content type of current playing media."""
        if not self.coordinator.data:
            return None
        media_info = self.coordinator.data.get("media_info")
        return MediaType.MUSIC if media_info else None
    
    @property
    def media_image_url(self) -> str | None:
        """Image URL of current playing media."""
        if not self.coordinator.data:
            return None
        media_info = self.coordinator.data.get("media_info")
        return media_info.icon_url if media_info else None
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity specific state attributes."""
        attrs = {
            ATTR_AUDIO_MODES: self._audio_modes,
        }
        
        if self.coordinator.data:
            attrs[ATTR_AUDIO_MODE] = self.coordinator.data.get("audio_mode")
            attrs[ATTR_AUDIO_TYPE] = self.coordinator.data.get("audio_type")
            
            # Add media info attributes
            media_info = self.coordinator.data.get("media_info")
            if media_info:
                attrs["media_service"] = media_info.service
                attrs["media_audio_format"] = media_info.audio_format
                if media_info.bit_rate:
                    attrs["media_bitrate"] = media_info.bit_rate
            
        return attrs
    
    async def async_turn_on(self) -> None:
        """Turn the media player on."""
        await self.coordinator.device.power.on()
        await self.coordinator.async_request_refresh()
    
    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self.coordinator.device.power.off()
        await self.coordinator.async_request_refresh()
    
    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        volume_db = self._level_to_db(volume)
        await self.coordinator.device.volume.set(volume_db)
        await self.coordinator.async_request_refresh()
    
    async def async_volume_up(self) -> None:
        """Volume up the media player."""
        await self.coordinator.device.volume.up(2.0)  # 2dB steps
        await self.coordinator.async_request_refresh()
    
    async def async_volume_down(self) -> None:
        """Volume down the media player."""
        await self.coordinator.device.volume.down(2.0)  # 2dB steps
        await self.coordinator.async_request_refresh()
    
    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) media player."""
        if mute:
            await self.coordinator.device.volume.mute()
        else:
            await self.coordinator.device.volume.unmute()
        self._is_muted = mute
        self.async_write_ha_state()
    
    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        await self.coordinator.device.source.select_by_name(source)
        await self.coordinator.async_request_refresh()
    
    async def async_set_audio_mode(self, mode_index: int | None = None, mode_name: str | None = None) -> None:
        """Set audio processing mode (service call)."""
        await self.coordinator.async_set_audio_mode(mode_index, mode_name)
    
    async def async_set_room_perfect(self, position_index: int | None = None, position_name: str | None = None) -> None:
        """Set RoomPerfect position (service call)."""
        if not self.coordinator.available:
            raise Exception("Device not available")
            
        # This would need to be implemented in the library first
        _LOGGER.warning("RoomPerfect control not yet implemented in library")
    
    async def async_set_lipsync(self, delay_ms: int) -> None:
        """Set lipsync delay (service call)."""
        if not self.coordinator.available:
            raise Exception("Device not available")
            
        # This would need to be implemented in the library first
        _LOGGER.warning("Lipsync control not yet implemented in library")
    
    def _db_to_level(self, db: float) -> float:
        """Convert dB to volume level (0-1)."""
        # Clamp to our UI range
        db = max(MIN_VOLUME_DB, min(MAX_VOLUME_DB, db))
        # Linear mapping from dB range to 0-1
        return (db - MIN_VOLUME_DB) / (MAX_VOLUME_DB - MIN_VOLUME_DB)
    
    def _level_to_db(self, level: float) -> float:
        """Convert volume level (0-1) to dB."""
        # Ensure level is in 0-1 range
        level = max(0.0, min(1.0, level))
        # Linear mapping from 0-1 to dB range
        return MIN_VOLUME_DB + (level * (MAX_VOLUME_DB - MIN_VOLUME_DB))
    
    async def async_media_play(self) -> None:
        """Send play command."""
        if self.coordinator.device.media:
            await self.coordinator.device.media.play()
            await self.coordinator.async_request_refresh()
    
    async def async_media_pause(self) -> None:
        """Send pause command."""
        if self.coordinator.device.media:
            await self.coordinator.device.media.pause()
            await self.coordinator.async_request_refresh()
    
    async def async_media_next_track(self) -> None:
        """Send next track command."""
        if self.coordinator.device.media:
            await self.coordinator.device.media.next_track()
            await self.coordinator.async_request_refresh()
    
    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        if self.coordinator.device.media:
            await self.coordinator.device.media.previous_track()
            await self.coordinator.async_request_refresh()

    async def async_browse_media(
        self,
        media_content_type: str | None = None,
        media_content_id: str | None = None,
    ) -> BrowseMedia:
        """Browse AES67 streams discovered via ZMAN/SAP."""
        source_name = self.source or ""
        if "aes67" not in source_name.lower():
            raise BrowseError("AES67 media browse is only available when the source is set to AES67")

        zman = await self.coordinator.async_get_zman()
        discovered = await self.hass.async_add_executor_job(zman.get_discovered_sources)

        children = [
            BrowseMedia(
                title=uri.removeprefix("sap://"),
                media_class=MediaClass.MUSIC,
                media_content_id=uri,
                media_content_type=MEDIA_TYPE_AES67,
                can_play=True,
                can_expand=False,
            )
            for uri in discovered
        ]

        return BrowseMedia(
            title="AES67 Streams",
            media_class=MediaClass.DIRECTORY,
            media_content_id="aes67",
            media_content_type=MEDIA_TYPE_AES67,
            can_play=False,
            can_expand=True,
            children=children,
        )

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        **kwargs: Any,
    ) -> None:
        """Play an AES67 stream by routing it via ZMAN."""
        if media_type != MEDIA_TYPE_AES67:
            _LOGGER.warning("Unsupported media type: %s", media_type)
            return

        zman = await self.coordinator.async_get_zman()
        await self.hass.async_add_executor_job(
            zman.create_path,
            media_id,  # source SAP URI
            [8, 9],    # output_channels: Lyngdorf L/R on OEM I2S group 30
        )
        _LOGGER.info("Routed AES67 stream %s to Lyngdorf channels 8,9", media_id)