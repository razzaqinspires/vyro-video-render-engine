# VYRO Video Render Engine

**Release:** 1.2.0 · **Python:** 3.11+ · **Output:** H.264 MP4, 1080×1920, 30 FPS.

## Responsibilities
- Render approved `ContentPackage` scenes into vertical MP4.
- Use supplied, licensed, or generated still-image assets and optional WAV/MP3/M4A narration.
- Validate the resulting video with ffprobe and write a SHA-256 manifest.
- Isolate demo uploads and outputs by hashed demo ID with configurable TTL.

Browser-side video editing remains experimental and exports WebM where supported. This service produces the server-side MP4 master. It does not generate speech, create scripts, or publish to Instagram.

## API
- `GET /health`
- `POST /v1/assets` — requires service bearer token and `X-Vyro-Demo-ID`.
- `POST /v1/render` — requires `X-Vyro-Demo-ID` and `content_package.review_approved=true`.
- `GET /v1/renders/{render_id}/download` — requires the same demo ID.

Assets and renders are temporary. Defaults: assets 48 hours, render outputs 72 hours. `demo_id` is a browser-local namespace, not authentication; use private deployment/network controls for production workloads.

## Install
```bash
pip install -e '.[api,dev]'
uvicorn vyro_video_render_engine.api:app --host 0.0.0.0 --port 8104
pytest -q
```

FFmpeg and ffprobe must be installed on the host and available in `PATH`.
