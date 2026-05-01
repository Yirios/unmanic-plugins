# Changelog

## v0.2.0
- Upgraded plugin architecture to use Probe/Parser/StreamMapper (matching Nvidia plugin)
- Added proper stream mapping with first-track-only selection for video and audio
- Added FFmpeg progress parsing for Unmanic UI integration
- `-preset` setting is now properly passed to hevc_qsv encoder
- Changed preset options to QSV-supported values (veryfast through veryslow)
- Added `-movflags +faststart` for MP4 streaming optimization
- Removed `Extend` custom args setting
- Improved UI form configuration with conditional field visibility
