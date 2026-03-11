"""Main device class for Steinway P100."""

import logging
from typing import Callable, Optional

from .connection import BaseConnection, TCPConnection, SerialConnection
from .controls import PowerControl, VolumeControl, SourceControl, AudioModeControl
from .constants import Zone, FeedbackLevel, DEFAULT_TCP_PORT
from .protocol import CommandBuilder
from .api import MediaApiClient


logger = logging.getLogger(__name__)


class SteinwayP100Device:
    """High-level interface to Steinway P100."""

    def __init__(self, connection: Optional[BaseConnection] = None, host: Optional[str] = None):
        """
        Initialize device.

        Args:
            connection: Connection instance. If None, use from_tcp() or from_serial()
            host: Device hostname/IP for HTTP API (optional)
        """
        self._connection = connection
        self._host = host

        # Initialize controls
        self.power = PowerControl(connection, Zone.MAIN) if connection else None
        self.zone2_power = PowerControl(connection, Zone.ZONE2) if connection else None
        self.volume = VolumeControl(connection, Zone.MAIN) if connection else None
        self.zone2_volume = (
            VolumeControl(connection, Zone.ZONE2) if connection else None
        )
        self.source = SourceControl(connection) if connection else None
        self.audio_mode = AudioModeControl(connection) if connection else None
        
        # Initialize media API client if host provided
        self.media = MediaApiClient(host) if host else None

    @classmethod
    def from_tcp(cls, host: str, port: int = DEFAULT_TCP_PORT) -> "SteinwayP100Device":
        """
        Create device with TCP connection.

        Args:
            host: IP address or hostname
            port: TCP port (default: 84)
        """
        connection = TCPConnection(host, port)
        return cls(connection, host=host)

    @classmethod
    def from_serial(cls, port: str, baudrate: int = 115200) -> "SteinwayP100Device":
        """
        Create device with serial connection.

        Args:
            port: Serial port (e.g., /dev/ttyUSB0 or COM1)
            baudrate: Baud rate (default: 115200)
        """
        connection = SerialConnection(port, baudrate)
        return cls(connection)

    async def connect(self) -> None:
        """Connect to the device."""
        if not self._connection:
            raise ValueError("No connection configured")

        await self._connection.connect()

        # Set feedback level
        await self.set_feedback_level(FeedbackLevel.STATUS)

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        if self._connection:
            await self._connection.disconnect()

    async def set_feedback_level(self, level: FeedbackLevel) -> None:
        """Set the feedback verbosity level."""
        command = CommandBuilder.feedback_level(level)
        await self._connection.send_command(command)
        self._connection.set_feedback_level(level)

    def set_notification_callback(
        self, callback: Optional[Callable[[str], None]]
    ) -> None:
        """Set a callback for unsolicited device notifications."""
        if self._connection:
            self._connection.set_notification_callback(callback)

    @property
    def is_connected(self) -> bool:
        """Check if connected to device."""
        return self._connection and self._connection.is_connected

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
