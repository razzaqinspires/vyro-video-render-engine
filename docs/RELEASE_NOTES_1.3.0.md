# VYRO Video Render Engine 1.3.0

## Added
- Strict multi-track Timeline Schema 1.0 with video, image, text and audio clips.
- FFmpeg composition pipeline for layered visuals and mixed audio.
- Source trim, placement, fit mode, audio gain and audio fades.
- Per-demo asset validation, file signature checks and render ownership checks.
- API request controls for render preset, CRF, project duration and clip count.
- `ffprobe` output inspection and SHA-256 render manifest.
- API OpenAPI documentation and editor integration contract.
- Legacy ContentPackage CLI compatibility command.

## Security and operational safeguards
- Final render requires explicit `review_approved=true`.
- Service key uses constant-time comparison.
- Assets use opaque file IDs and demo namespaces; filenames are display metadata only.
- Request payloads and timeline fields are bounded.
- In-process render concurrency is limited by configuration.

## Known limitations
- Not a full NLE: no interactive browser timeline UI, keyframing, transitions, masks, chroma key, tracking, proxy media or multi-cam.
- Browser preview must not be treated as pixel-identical to FFmpeg output.
- Render execution is synchronous and the semaphore is process-local; production scale requires durable queue + shared object storage.
- Malware scanning and copyright ownership verification are not built into this component.
