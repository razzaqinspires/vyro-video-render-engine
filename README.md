# VYRO Video Render Engine

**Release:** 1.3.0 · **Python:** 3.11+ · **Renderer:** FFmpeg · **Default master:** H.264 MP4

VYRO Video Render Engine is the server-side rendering component for VYRO MEDIA Creative Studio. Version 1.3 adds a multi-track timeline contract while retaining the v1.2 ContentPackage adapter for existing AI Content Engine workflows.

## What this component does

- Renders a multi-track timeline containing video, still images, title overlays and multiple audio clips.
- Supports source trim, timeline placement, cover/contain fit, audio volume, audio fade-in/out and visual fade metadata.
- Produces H.264/AAC MP4, probes the result with `ffprobe`, and writes a SHA-256 render manifest.
- Namespaces uploaded assets and rendered output by a browser-supplied demo ID, with server-side service-key authentication and TTL cleanup.
- Requires an explicit human approval flag before any final render request is accepted.
- Retains `/v1/render` payload compatibility only through the `ContentPackage` CLI adapter; the v1.3 HTTP API accepts the new `Timeline` schema.

This service is the final render backend, not the browser editing interface. Timeline editing, scrubbing, clip selection, undo/redo, project persistence and interactive preview belong to the VYRO MEDIA editor frontend. Speech synthesis belongs to VYRO AI Voice Studio. Content/script generation belongs to VYRO AI Content Engine. Publishing is intentionally outside this engine.

## Architecture

```text
VYRO MEDIA /editor.html
  ├── Project + Timeline state
  ├── Media Bin + browser preview
  ├── Track / clip editor
  ├── Human Review gate
  └── Render Client
        │ HTTPS + Bearer service credential (server-to-server)
        ▼
VYRO Video Render Engine API
  ├── Authentication + demo namespace
  ├── Upload signature / size validation
  ├── Timeline schema validation
  ├── FFmpeg composition pipeline
  ├── ffprobe output verification
  └── SHA-256 manifest + temporary output storage
```

Suggested source structure:

```text
src/vyro_video_render_engine/
  api.py                 # FastAPI routes, auth, upload/render/download lifecycle
  cli.py                 # CLI commands
  models.py               # Strict timeline + legacy content contracts
  renderer.py             # FFmpeg graph builder, render, probe and manifest
  upload_validation.py    # Extension-independent file-signature checks
```

## Requirements

- Python 3.11 or newer.
- FFmpeg and ffprobe installed and accessible in `PATH`.
- For API mode: a private deployment behind HTTPS and a long random service key.

Check the binaries:

```bash
ffmpeg -version
ffprobe -version
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -e '.[api,dev]'
cp .env.example .env
```

Set a unique `VYRO_SERVICE_API_KEY` in `.env`. Never expose this credential to browser JavaScript or commit `.env`.

## Run the API

```bash
uvicorn vyro_video_render_engine.api:app --host 127.0.0.1 --port 8104
```

OpenAPI documentation is available at `http://127.0.0.1:8104/docs`. For production, use a private HTTPS deployment, secret manager, request-size limits at the reverse proxy, persistent storage with lifecycle cleanup, and authenticated user-to-demo authorization. The built-in demo ID is a namespace boundary, not a user identity or complete end-user authentication system.

### API contract

All `/v1/*` routes require:

```http
Authorization: Bearer <VYRO_SERVICE_API_KEY>
X-Vyro-Demo-ID: VYRO-DEMO-<8-to-40-hex-characters>
```

1. `POST /v1/assets` — upload a base64-encoded media asset. The service checks allowed extension, decoded size and file signature. Response contains an `asset_ref`.
2. `POST /v1/render` — accepts `{ "timeline": { ... }, "review_approved": true }`. A false or missing approval is rejected with HTTP 409. Render happens synchronously in this service process; it is not a durable distributed job queue.
3. `GET /v1/renders/{render_id}/download` — retrieves the render only when the caller supplies the matching demo namespace.
4. `GET /health` — service health and engine version.

See `docs/API.md` for example requests and response shapes.

## Render from the CLI

```bash
vyro-render render examples/timeline.json \
  --output output/vyro-master.mp4 \
  --assets-dir assets \
  --preset medium \
  --crf 20

vyro-render inspect output/vyro-master.mp4
```

The example timeline contains placeholders for `asset_ref`. Replace them with actual paths relative to the assets directory. The CLI accepts a timeline object directly or an object with a top-level `timeline` key.

## Timeline essentials

The schema uses seconds for all time values. A project contains tracks and clips. Track order controls visual layering: higher `order` values are composited later. `video` tracks accept video/image clips; `overlay` tracks accept text/image clips; `audio` tracks accept audio clips. Clip `start_seconds` is the position on the final timeline; `source_in_seconds` trims source video/audio before the clip begins. Text is rendered as a transparent PNG layer. Details and complete field constraints are in `docs/TIMELINE_SCHEMA.md`.

## Compatibility

The v1.2 ContentPackage contract remains supported through:

```bash
vyro-render render-legacy examples/content_package.json \
  --output output/legacy-master.mp4 \
  --assets-dir assets
```

The new HTTP `/v1/render` endpoint intentionally uses the explicit multi-track timeline and does not silently accept legacy payloads. This avoids ambiguous request shapes. See `docs/MIGRATION_1.2_TO_1.3.md`.

## Storage and retention

Defaults from `.env.example`:

- Uploaded media: 48 hours.
- Render output: 72 hours.
- Maximum asset upload: 20 MiB default, hard-capped at 50 MiB by service configuration.
- Maximum timeline duration: 180 seconds by default.
- Maximum timeline clip count: 80 by default.
- In-process concurrent render jobs: 1 by default.

The render lock is in-process only. Multiple API workers or replicas require an external queue/lock and shared object storage to guarantee system-wide limits and retrieval consistency. Production deployment should use signed object URLs or a private storage adapter rather than relying on ephemeral local disk.

## Security and rights controls

- Never place service API keys in frontend code, project JSON, logs, or generated bundles.
- Enforce user authorization at the VYRO backend before proxying requests to this service.
- Validate content ownership, usage rights, and model/voice consents before final render.
- The service requires `review_approved=true`; this is an approval declaration from the trusted backend, not an identity-verification mechanism.
- Upload signatures are checked for supported file types. The service does not perform malware scanning or verify copyright ownership.
- Do not use a public deployment with the shared demo key or trust `X-Vyro-Demo-ID` as an end-user credential.

## Test and quality checks

```bash
pytest
ruff check .
ruff format --check .
python -m compileall -q src tests
```

A render integration test runs FFmpeg and is skipped only when FFmpeg/ffprobe are unavailable. Test coverage includes strict timeline validation, asset signatures, API auth gates, approval gate, and real MP4 render/probe/manifest output.

## Release notes

See `CHANGELOG.md` and `docs/RELEASE_NOTES_1.3.0.md`.

## License

Proprietary. See `LICENSE`.
