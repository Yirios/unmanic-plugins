# Changelog

## v0.3.6
- Fix repeat loop: return data instead of None when probe fails

## v0.3.5
- Add GPU framerate adjustment via vpp_qsv (framerate=N)
- Change FPS now visible in both CPU and HW decode modes

## v0.3.4
- Hardcode -look_ahead 1 (forced on, removed from user settings)

## v0.3.3
- Add Rate Control Mode selector (CQP / VBR), mutually exclusive presentation
- CQP mode: -global_quality without mixed bitrate params (fix quality control)
- VBR mode: -b:v -maxrate -bufsize
- Lookahead forced on, user adjustable depth
- Default bitrate values lowered to ~1k range

## v0.3.2
- Fix -hwaccel qsv options: bypass __build_args to avoid dedup of duplicate values

## v0.3.1
- Fix -hwaccel qsv options placement: use generic_options instead of advanced_options so they go before -i

## v0.3.0
- Added "Copy Video" option to skip video encoding and copy video stream unchanged
- Added "Enable Hardware Decoding" option to toggle QSV hardware decoding (-hwaccel qsv)
- Added GPU filter chain (vpp_qsv) with denoise and scale settings for hardware decoding mode
- CPU filter fields (hqdn3d, scale, fps, crop) hidden when hardware decoding is enabled
- FPS and Crop settings hidden when hardware decoding is enabled
- Added "Enable Audio Filter" option to make audio filter (-af) configurable
- Renamed "Enable Filter" to "Enable Video Filter" for clarity

## v0.2.0
- Upgraded plugin architecture to use Probe/Parser/StreamMapper (matching Nvidia plugin)
- Added proper stream mapping with first-track-only selection for video and audio
- Added FFmpeg progress parsing for Unmanic UI integration
- `-preset` setting is now properly passed to hevc_qsv encoder
- Changed preset options to QSV-supported values (veryfast through veryslow)
- Added `-movflags +faststart` for MP4 streaming optimization
- Removed `Extend` custom args setting
- Improved UI form configuration with conditional field visibility
