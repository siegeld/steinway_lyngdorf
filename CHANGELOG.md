# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Real-time state updates via push notifications — device pushes (VOL, SRC, MUTE, POWER, AUDMODE, AUDTYPE) are parsed and update HA state instantly
- Notification callback in connection layer (`set_notification_callback`) for unsolicited `!`-prefixed messages
- AES67 stream info clears immediately on source change away from AES67

### Changed
- Poll interval increased from 5s to 30s (polling is now a fallback/keepalive)
- Mute state now tracked via push notifications instead of hardcoded False

### Fixed
- Mute state now reflects actual device state via push notifications
- External changes (remote, web UI) now reflected in HA within ~1 second instead of up to 5s

## [0.3.6] - 2025-07-31

### Fixed
- Media metadata now displays correctly in Home Assistant (added media_content_id, media_content_type, media_image_url)
- Mute functionality in Home Assistant (tracks state locally since P100 doesn't respond to MUTE? reliably)

## [0.3.5] - 2025-07-31

### Fixed
- Changed debug WARNING logs to DEBUG level to reduce log noise
- Fixed DNS resolution for short hostnames in Docker environments
- HTTP API now correctly uses short hostnames instead of FQDNs

## [0.3.4] - 2025-07-31
## [0.3.3] - 2025-07-31
## [0.3.2] - 2025-07-31
## [0.3.1] - 2025-07-31
## [0.3.0] - 2025-07-31
## [0.2.1] - 2025-07-31
## [0.2.0] - 2025-07-31
## [0.1.3] - 2025-07-31
## [0.1.2] - 2025-07-31

### Added
- Source control functionality for main zone
- CLI commands for source selection (list, get, set, next, prev)
- Support for selecting sources by name or index
- Source caching to minimize API calls
- Audio processing mode control (Dolby, DTS, Auro-3D, etc.)
- CLI commands for audio mode selection
- Audio input type information query
- Home Assistant custom component (media_player entity)
- Automatic reconnection in Home Assistant
- Custom services for audio mode selection
- HACS compatibility

### Changed
- Nothing yet

### Fixed
- Python 3.9 compatibility for type hints

## [0.1.1] - 2025-07-31

### Added
- Volume control with mute functionality
- CLI volume commands (get, set, up, down, mute, unmute)
- Support for Zone 2 volume control
- Step-based volume adjustment
- Monitor mode for debugging communication

### Changed
- Improved error handling for device timeouts
- Enhanced CLI output formatting

### Fixed
- MUTE? command timeout issues
- Volume response parsing

## [0.1.0] - 2025-07-31

### Added
- Initial release
- Basic connection framework (TCP and Serial)
- Power control for main zone and Zone 2
- Asynchronous command/response protocol
- CLI tool with environment variable support
- Basic project structure and documentation
- Virtual environment setup
- Development tooling (Makefile, black, ruff, mypy)

## Roadmap

### Version 0.2.0
- RoomPerfect position and voicing control
- Lipsync adjustment
- System information queries
- Multiview control (P200/P300)
- Speaker configuration management
- Advanced audio settings

### Version 0.3.0
- Auto-discovery via Bonjour
- WebSocket support for real-time updates
- Home Assistant UI enhancements
- Scene management
- Unit tests with >80% coverage

### Version 1.0.0
- Full protocol implementation
- Comprehensive test coverage
- Production-ready Home Assistant component
- Complete API documentation
- Serial connection support

[Unreleased]: https://github.com/siegeld/steinway-p100/compare/v0.3.6...HEAD
[0.3.6]: https://github.com/siegeld/steinway-p100/compare/v0.3.5...v0.3.6
[0.3.5]: https://github.com/siegeld/steinway-p100/compare/v0.3.4...v0.3.5
[0.3.4]: https://github.com/siegeld/steinway-p100/compare/v0.3.3...v0.3.4
[0.3.3]: https://github.com/siegeld/steinway-p100/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/siegeld/steinway-p100/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/siegeld/steinway-p100/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/siegeld/steinway-p100/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/siegeld/steinway-p100/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/siegeld/steinway-p100/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/siegeld/steinway-p100/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/siegeld/steinway-p100/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/siegeld/steinway-p100/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/siegeld/steinway-p100/releases/tag/v0.1.0
