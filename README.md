<div align="center">

<img src="build/icon.svg" alt="YT Downloader Logo" width="96" height="96">

# YT Downloader

**Download YouTube videos and audio to your desktop — with a single click.**

[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/gloooomed/YT_Downloader/releases)
[![Version](https://img.shields.io/badge/Version-1.0.9-blue?style=for-the-badge)](https://github.com/gloooomed/YT_Downloader/releases)
[![Electron](https://img.shields.io/badge/Built%20with-Electron-47848F?style=for-the-badge&logo=electron&logoColor=white)](https://www.electronjs.org/)
[![yt--dlp](https://img.shields.io/badge/Powered%20by-yt--dlp-FF0000?style=for-the-badge)](https://github.com/yt-dlp/yt-dlp)

[Features](#features) · [Installation](#installation) · [Usage](#usage) · [How It Works](#how-it-works) · [Troubleshooting](#troubleshooting) · [Contributing](#contributing)

</div>

---

## Overview

**YT Downloader** is a Windows desktop application for saving YouTube videos and audio locally. It pairs an Electron and React interface with a Python (`yt-dlp`) backend, and takes care of its own dependencies — FFmpeg and yt-dlp are fetched automatically the first time they are needed, so there is nothing to configure by hand.

---

## Features

| Feature | Description |
|---|---|
| **Metadata Preview** | Paste a URL and fetch the video title and every resolution actually available for it before downloading |
| **Video Export** | Download as MP4, choosing from the resolutions offered or a best/smallest preset |
| **Audio Export** | Extract audio-only as MP3, M4A, or Opus |
| **Live Progress** | Real-time percentage, download speed, and ETA, plus a distinct status while FFmpeg merges audio and video |
| **Automatic FFmpeg Provisioning** | Downloads and installs FFmpeg locally under `%LOCALAPPDATA%\YTDownloader\bin` if it isn't already available |
| **Automatic yt-dlp Provisioning & Upgrades** | Installs yt-dlp on demand and upgrades it on every launch, so format extraction keeps working as YouTube changes its streaming formats |
| **Custom Save Location** | Choose any output folder via a native directory picker |

---

## Installation

### Option 1 — Windows Installer *(Recommended)*

1. Download the latest installer from [GitHub Releases](https://github.com/gloooomed/YT_Downloader/releases)
2. Run `YT-Downloader-Setup-<version>.exe` and follow the setup wizard
3. Launch **YT Downloader** from the Start Menu or desktop shortcut

> **Note:** The app requires Python 3.9+ to be installed and available on `PATH`. FFmpeg and yt-dlp are fetched automatically on first use.

---

### Option 2 — Build From Source *(Development)*

1. Clone the repository:
   ```bash
   git clone https://github.com/gloooomed/YT_Downloader.git
   cd YT_Downloader
   ```

2. Install dependencies:
   ```bash
   npm install
   python -m pip install -r requirements.txt
   ```

3. Run in development mode (two terminals):
   ```bash
   npm run dev
   npm run electron:dev
   ```

4. Build a production installer:
   ```bash
   npm run build
   npm run package
   ```
   The packaged NSIS installer is written to `dist-electron/`.

---

## Usage

1. Paste a YouTube URL into the input field and click **Fetch Details**
2. Choose **Video & Audio** or **Audio Only**
3. Pick a quality (video) or format (audio):

   | Media Type | Options |
   |---|---|
   | **Video** | Best, any detected resolution (e.g. 1080p, 720p), or Small |
   | **Audio** | MP3, M4A (original), Opus |

4. Confirm or change the **Save Location**
5. Click **Start Download** and watch progress in the terminal-style status panel

---

## How It Works

1. **Metadata fetch** — The Electron main process (`main.js`) spawns the Python bridge (`bridge.py`) as a child process, which queries `yt-dlp` for the video title and available formats.
2. **Dependency check** — Before any extraction, the backend resolves FFmpeg and yt-dlp, auto-installing either one to `%LOCALAPPDATA%\YTDownloader\bin` if missing, and silently upgrading yt-dlp on every run.
3. **Download** — `yt-dlp` streams the selected format; progress events are parsed and forwarded to the UI over IPC as JSON lines.
4. **Processing** — If the video and audio streams need merging, or audio needs converting, FFmpeg runs as a post-processing step while the UI shows a "processing" state.
5. **UI** — `preload.js` exposes a scoped `window.api` to the renderer via `contextBridge`, keeping Node integration disabled in `src/App.jsx`.

---

## Requirements

| Requirement | Needed For |
|---|---|
| Windows 10/11 | Running the packaged application |
| Python 3.9+ on `PATH` | Running the app (the Python bridge is not bundled into the installer) |
| Node.js 20+ | Building from source or running in development mode |

FFmpeg and yt-dlp are **not** required ahead of time — the app installs them itself on first use.

---

## Project Structure

```
YT_Downloader/
│
├── main.js                  # Electron main process, IPC handlers
├── preload.js                # Context-isolated renderer API
├── bridge.py                  # CLI entry point for the Python backend
│
├── src/
│   ├── App.jsx                 # React UI
│   ├── index.css                # Styles
│   ├── main.jsx                  # React entry point
│   └── yt_downloader/              # Download logic, CLI, and yt-dlp/FFmpeg provisioning
│       ├── downloader.py             # Format resolution, FFmpeg/yt-dlp provisioning, download
│       ├── cli.py                     # Standalone terminal downloader
│       ├── paths.py                    # Output directory resolution
│       └── prompts.py                   # Terminal prompt helpers
│
└── build/
    └── installer.nsh              # Custom NSIS install-log display
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Stuck on "FFmpeg Missing (360p Max)" | The app auto-installs FFmpeg on first use; if it fails, check your internet connection and that `curl.exe` is available (bundled with Windows 10+) |
| `yt-dlp could not be initialized automatically` | Ensure Python is installed and on `PATH`, then run `python -m pip install yt-dlp` manually |
| Download fails immediately after a URL change | Click **Fetch Details** again — a fetched URL must match the URL in the input field before downloading |
| Only low resolutions available | yt-dlp auto-upgrades on launch, but you can force it with `python -m pip install --upgrade yt-dlp` |
| Installer log window looks empty | The custom NSIS log page (`build/installer.nsh`) mirrors install progress; give it a moment on slower disks |

---

## Contributing

Contributions are welcome. To get started:

```bash
git clone https://github.com/gloooomed/YT_Downloader.git
cd YT_Downloader
```

1. Create a feature branch: `git checkout -b feature/my-improvement`
2. Make your changes
3. Verify both the desktop app (`npm run electron:dev`) and the standalone CLI (`ytd`) still work
4. Submit a pull request with a clear description of what changed and why

For bug reports or feature requests, please [open an issue](https://github.com/gloooomed/YT_Downloader/issues).

---

## Release Notes

### v1.0.9 — Auto-Upgrading yt-dlp & Installer Logging
- Auto-upgrade yt-dlp on every launch, fixing a 360p-only format regression caused by stale yt-dlp versions
- Added a custom NSIS install-log display, matching the VLC-style installer experience
- Corrected invalid CSS shorthand properties and replaced the raster logo with an SVG

### v1.0.8 — Reliable Dependency Downloads
- Switched to `curl.exe` for FFmpeg and yt-dlp auto-download, fixing SSL failures on fresh Windows installs where Python's `urllib` lacked trusted certificates

### v1.0.7 — Smaller Installer
- Removed bundled FFmpeg to cut installer size to roughly 50 MB
- FFmpeg now installs on demand into local AppData instead of shipping with every release

### v1.0.6 — Installer & Fallback Chain
- Configured the NSIS setup installer with a multi-tier fallback for locating yt-dlp and FFmpeg
- Disabled electron-builder auto-publish for local packaging

### v1.0.3 — v1.0.5 — Format Resolution & Auto-Fallback
- Redesigned the UI around a portfolio-style design system and fixed the Python bridge path
- Added automatic FFmpeg fallback and refined video format/resolution selection

### v1.0.1 — Electron Migration
- Migrated the application from a PyInstaller-bundled Tkinter GUI to Electron and React
- Removed legacy packaging files in favor of a portable installer release

### Earlier — Terminal Origins
- Started as a terminal-only downloader with FFmpeg support for audio conversion and video/audio merging, later wrapped in a bundled Windows GUI before the Electron rewrite

---

<div align="center">

Made for anyone who wants their videos, not just a streaming link.

If this project is useful to you, consider giving it a star on [GitHub](https://github.com/gloooomed/YT_Downloader).

</div>
