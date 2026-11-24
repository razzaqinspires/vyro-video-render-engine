# VYRO Video Render Engine API

Base URL examples use `http://127.0.0.1:8104`. All `/v1/*` routes require a service bearer key and a demo ID namespace.

## Upload media

`POST /v1/assets`

```http
Authorization: Bearer <SERVICE_KEY>
X-Vyro-Demo-ID: VYRO-DEMO-a1b2c3d4
Content-Type: application/json
```

```json
{
  "filename": "product-shot.png",
  "data_base64": "<base64-encoded-bytes>"
}
```

Response:

```json
{
  "asset_ref": "<namespace>/<opaque-file-id>.png",
  "bytes": 24018,
  "media_type": "png",
  "sha256": "...",
  "expires_after_hours": 48
}
```

Accepted types: PNG, JPEG, WebP, WAV, MP3, M4A, MP4, MOV. File signature and byte size are validated. Browser clients should call a trusted VYRO server adapter; do not send the service key from the browser.

## Render final output

`POST /v1/render`

```json
{
  "review_approved": true,
  "review_note": "Human review completed by the project owner.",
  "output_preset": "medium",
  "output_crf": 20,
  "timeline": {
    "schema_version": "1.0",
    "title": "Product Story",
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "duration_seconds": 8,
    "background_color": "#050708",
    "tracks": [
      {"track_id": "V1", "name": "Footage", "kind": "video", "order": 0},
      {"track_id": "T1", "name": "Titles", "kind": "overlay", "order": 1},
      {"track_id": "A1", "name": "Music", "kind": "audio", "order": 2}
    ],
    "clips": [
      {"clip_id": "shot001", "track_id": "V1", "kind": "image", "start_seconds": 0, "duration_seconds": 8, "asset_ref": "<asset-ref>"},
      {"clip_id": "title001", "track_id": "T1", "kind": "text", "start_seconds": 1, "duration_seconds": 4, "text": "A clearer way to create", "font_size": 72},
      {"clip_id": "audio001", "track_id": "A1", "kind": "audio", "start_seconds": 0, "duration_seconds": 8, "asset_ref": "<audio-ref>", "volume": 0.8}
    ]
  }
}
```

`review_approved` must be exactly `true`; otherwise API returns HTTP 409. The timeline is validated before any render work begins.

Response includes `render_id`, `status`, `manifest`, `download_url`, and expiry information. The manifest includes output dimensions, duration, codec details and SHA-256 checksum.

## Download

`GET /v1/renders/{render_id}/download`

Use the same bearer key and exact same `X-Vyro-Demo-ID` used to create the render. Different demo IDs cannot access one another's uploaded files or render outputs.

## Status codes

| Code | Meaning |
|---|---|
| 200 | Request completed |
| 400 | Demo or render ID format invalid |
| 401 | Missing/incorrect service key |
| 403 | Asset/render belongs to another demo namespace |
| 409 | Human approval missing |
| 413 | Upload/timeline exceeds configured limits |
| 415 | Unsupported extension or mismatched file signature |
| 422 | Invalid timeline or render pipeline error |
| 429 | In-process render capacity currently full |
| 503 | Service key or service configuration missing |
