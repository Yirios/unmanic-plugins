
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository hosts Unmanic plugins for media transcoding and workflow automation. Unmanic is a media server that processes files through a plugin pipeline. Plugins are Python modules that hook into Unmanic's processing stages (e.g., `on_worker_process`, `on_library_management_file_test`).

The repository is structured as a plugin repository: each plugin resides in `source/<plugin_name>/` and includes required metadata. The `scripts/generate_repository.py` script builds a distribution-ready `repo/` directory containing zipped plugins and a `repo.json` manifest for Unmanic to consume.

## Repository Structure

- `config.json` – Repository metadata (ID, name, icon).
- `source/` – Each subdirectory is a separate plugin.
  - `plugin.py` – Main plugin entry point, implementing Unmanic plugin runners.
  - `info.json` – Plugin metadata (ID, name, version, author, tags, priorities).
  - `changelog.md` – Version history.
  - `lib/ffmpeg/` – Shared helper library for building FFmpeg commands (copied from [unmanic.plugin.helpers.ffmpeg](https://github.com/Josh5/unmanic.plugin.helpers.ffmpeg)).
  - `.gitignore` – Required per plugin to exclude build artifacts.
- `scripts/generate_repository.py` – Build script that zips plugins, installs dependencies, and generates `repo.json`.
- `.github/workflows/plugin-checker.yml` – CI workflow that validates plugin structure and auto‑deploys the `repo` branch on `master`/`official` pushes.
- `docs/` – Contribution guidelines, issue/PR templates.

## Branching

- `master` / `official` – Main development branches; pushes trigger CI and deploy the generated `repo/` to the `repo` branch.
- `repo` – Contains the built repository (`repo.json` and plugin ZIPs) served via GitHub raw URLs. This branch is updated automatically by the CI workflow.
- `template` – Holds the latest version of the generator script and CI configuration. The workflow pulls `scripts/` from this branch before building.

## Plugin Development

### Required Files
Every plugin directory must contain:
- `plugin.py` – Implements at least one Unmanic runner (e.g., `on_worker_process`).
- `info.json` – With `id`, `name`, `author`, `version`, `tags`, `description`, `compatibility` (list of supported Unmanic API versions), `platform` (list of OS platforms). The `priorities` object determines execution order (e.g., `"on_worker_process": 1`).
- `.gitignore` – Prevents accidental commits of `site‑packages/`, `node_modules/`, etc.
- `changelog.md` – Optional but recommended.

### Optional Files
The generator also copies these files if present:
- `icon.png` / `icon.jpg` – Plugin icon displayed in Unmanic's UI.
- `fanart.jpg` – Background art.
- `description.md` / `description.txt` – Extended description.
- `requirements.txt` – Python dependencies (installed during build).
- `package.json` – Node.js dependencies (built during build).

### Forbidden Files/Directories
- `site-packages/` – Python dependencies must be installed via `requirements.txt`; the build script will install them into a temporary location.
- `settings.json` – Plugin settings are defined in `plugin.py` using the `Settings` class (derived from `unmanic.libs.unplugins.settings.PluginSettings`).

### Dependencies
- **Python**: Add a `requirements.txt` in the plugin directory; the build script installs them with `pip install --target=site-packages`.
- **Node.js**: Add a `package.json`; the build script runs `npm install` and `npm run build`.

### Plugin Runners
Plugins can implement any of Unmanic's runner functions. The most common is `on_worker_process`, which receives a `data` dict containing `file_in`, `file_out`, `exec_command`, etc. The plugin must return the modified `data` dict.

Example skeleton:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from unmanic.libs.unplugins.settings import PluginSettings

class Settings(PluginSettings):
    settings = {
        "option1": "default",
        ...
    }

def on_worker_process(data):
    # plugin logic
    return data
```

### Using the FFmpeg Helper Library
The `lib/ffmpeg` module provides `Probe`, `Parser`, and `StreamMapper` classes to simplify FFmpeg command construction. Import it as `from <plugin_name>.lib.ffmpeg import Probe, Parser, StreamMapper`.

## Building the Repository

To generate the distributable plugin repository (e.g., for testing or local installation):

```bash
python scripts/generate_repository.py
```

This will:
1. Validate each plugin's `info.json`.
2. Install Python/Node dependencies per plugin.
3. Create a ZIP archive of each plugin (excluding `.git`, `.github`, etc.) in `repo/<plugin_name>/`.
4. Write a consolidated `repo.json` manifest to `repo/repo.json`.

The `repo/` directory is what Unmanic expects when adding a custom plugin repository URL (e.g., `https://raw.githubusercontent.com/.../repo/repo.json`).

## Quality Control

The CI workflow enforces:
- Presence of `.gitignore`, `info.json`, `plugin.py` in each plugin.
- Absence of `site-packages/` and `settings.json` directories.
- On push to `master` or `official`, the workflow runs the generator and deploys the `repo/` directory to the `repo` branch.

When contributing a new plugin, ensure it works with the latest Unmanic release and follows the [CONTRIBUTING.md](docs/CONTRIBUTING.md) guidelines (including the required copyright header in new Python files).

## Useful Commands

- **Generate repository**: `python scripts/generate_repository.py`
- **Check plugin structure**: Run the CI checks locally with the script from `.github/workflows/plugin-checker.yml`.
- **Add a new plugin**: Copy an existing plugin directory, update `info.json` and `plugin.py`, then run the generator.

## Notes

- The `lib/ffmpeg` code is duplicated across plugins; keep it in sync with upstream if updates are needed.
- Plugin versions must be incremented before rebuilding; the generator will skip plugins whose version‑numbered ZIP already exists in `repo/`.
- The repository URL in `config.json` is automatically derived from the git remote `origin` during generation.
- The `README.md` contains a placeholder repository URL; update it to match your fork's `repo` branch raw URL for users to add the repository to Unmanic.