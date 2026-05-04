# Unmanic Plugins by Yiriso

A collection of [Unmanic](https://docs.unmanic.app/docs/) plugins for media transcoding, stream selection, and file management.

## Plugins

### Better Network Streaming (intel) `v0.3.6`
Hardware-accelerated video transcoding using Intel QSV (Quick Sync Video) with `hevc_qsv` encoder.

- **Rate Control**: CQP (Constant Quality) or VBR (Bitrate) mode
- **Hardware Decoding**: Toggle `-hwaccel qsv` with GPU filter chain (`vpp_qsv`)
- **Video Filters**: Denoise, scale, framerate, crop (CPU and GPU filter chains)
- **Audio**: Copy or AAC encode with optional audio filter (`-af`)
- **Copy Video**: Option to skip video encoding entirely

### Better Network Streaming (nvidia) `v0.3.3`
Hardware-accelerated video transcoding using NVIDIA NVENC with `hevc_nvenc` encoder.

- **Rate Control**: VBR with constant quality (`-cq`)
- **Hardware Decoding**: Toggle CUDA hardware decoding with GPU filter chain
- **Video Filters**: Denoise (`bilateral_cuda` / `hqdn3d`), scale, FPS, crop
- **Audio**: Copy or AAC encode with optional audio filter
- **Copy Video**: Option to skip video encoding entirely

### Steam Selector `v0.1.2`
Selectively include or exclude streams (video/audio/subtitle) based on codec, language, or title keywords.

- Filter streams by codec name (e.g. `hevc`, `h264`)
- Filter by language or title tag keywords
- Copy all / copy selected / copy none per stream type

### Move and Rename `v0.0.3`
Basic file move and rename operations within the Unmanic pipeline.

### ffprobe viewer `v0.0.2`
View ffprobe output for files passing through the pipeline.

## Repository URL

```
https://raw.githubusercontent.com/Yirios/unmanic-plugins/repo/repo.json
```

Follow the [Unmanic documentation](http://docs.unmanic.app/docs/plugins/adding_a_custom_plugin_repo/) to add this repository.

## License

GPL v3. See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for contribution guidelines.
