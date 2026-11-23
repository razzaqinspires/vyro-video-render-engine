# VYRO Video Render Engine

**Repository:** `vyro-video-render-engine`  
**Purpose:** convert a validated AI content package into a technically checked vertical MP4 master.

## Responsibilities

- Consume `ContentPackage` JSON (the output contract of `vyro-ai-content-engine`).
- Resolve approved local image/video assets without accepting arbitrary shell commands.
- Produce vertical 1080×1920 frames using the VYRO visual system.
- Render H.264/AAC MP4 through FFmpeg with deterministic settings.
- Optionally add a cleared voice-over file.
- Run ffprobe validation and write a render manifest with hashes and media metadata.

This module does not generate original footage with a generative video model. It composes supplied/approved assets and motion-ready scenes. Version 1.0 supports still-image assets and text-only scene cards. Video-clip stitching and generative video providers are intentionally deferred to a later renderer version.

## System requirements

- Python 3.11+
- FFmpeg and ffprobe installed and available on PATH
- Licensed visual assets and approved narration/audio

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Render

```bash
vyro-render render examples/content_package.json --output output/vyro-test.mp4 --workdir output/work
vyro-render inspect output/vyro-test.mp4
```

## Design defaults

- Aspect ratio: 9:16 (1080×1920)
- Frame rate: 30 fps
- Video codec: H.264, yuv420p, faststart
- Audio codec: AAC when a voice-over is included
- Loudness: do not normalize source audio blindly; measure and review the actual file.
- No music is bundled. Use licensed or original audio only.

## Quality gates

Rendering fails on missing required assets, missing FFmpeg, invalid dimensions, or incomplete output. Human review remains required for factual accuracy, legibility, pacing, safe margins, rights, and platform disclosure.
