"""Constants for the Steinway Lyngdorf integration."""

DOMAIN = "steinway_lyngdorf"

# Services
SERVICE_SET_AUDIO_MODE = "set_audio_mode"
SERVICE_SET_ROOM_PERFECT = "set_room_perfect"
SERVICE_SET_LIPSYNC = "set_lipsync"

# Attributes
ATTR_AUDIO_MODE = "audio_mode"
ATTR_AUDIO_MODES = "audio_modes"
ATTR_AUDIO_TYPE = "audio_type"
ATTR_ROOM_PERFECT_POSITION = "room_perfect_position"
ATTR_ROOM_PERFECT_POSITIONS = "room_perfect_positions"
ATTR_LIPSYNC_DELAY = "lipsync_delay"

# Service attributes
ATTR_MODE_INDEX = "mode_index"
ATTR_MODE_NAME = "mode_name"
ATTR_POSITION_INDEX = "position_index"
ATTR_POSITION_NAME = "position_name"
ATTR_DELAY_MS = "delay_ms"

# AES67/ZMAN
CONF_ZMAN_HOST = "zman_host"
ZMAN_PORT = 80
MEDIA_TYPE_AES67 = "aes67_stream"