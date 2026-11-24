# Timeline Schema 1.0

This document defines the render contract exchanged between the VYRO MEDIA editor backend and VYRO Video Render Engine 1.3.0.

## Top-level fields

| Field | Type | Rules | Meaning |
|---|---|---|---|
| `schema_version` | string | `1.0` | Contract version |
| `title` | string | 1–160 chars | Project title |
| `width`, `height` | integer | 256–3840 | Render dimensions |
| `fps` | integer | 24–60 | Frame rate |
| `duration_seconds` | number | 1–180 by default service policy | Full output duration |
| `background_color` | hex color | `#RRGGBB` | Base canvas |
| `tracks` | array | 1–16 | Ordered track definitions |
| `clips` | array | 1–80 | Timeline clips |

## Track types

- `video`: video and still-image clips.
- `overlay`: text or image overlays.
- `audio`: audio clips only.

Each track has a unique `track_id`, human-readable `name`, integer `order`, and optional `muted` / `locked` flags. Track order controls visual compositing; a larger order is layered later. Muted audio tracks are omitted from the final mix. `locked` is editor metadata: it must not be used as a security permission.

## Clip types

All clips share `clip_id`, `track_id`, `kind`, `start_seconds`, `duration_seconds`, and `enabled`.

| Field | Type | Applies to | Description |
|---|---|---|---|
| `asset_ref` | string | video/image/audio | Demo-scoped upload reference or CLI-relative asset path |
| `source_in_seconds` | number | video/audio | Source trim in-point |
| `text` | string | text | Overlay copy, up to 500 chars |
| `font_size` | integer | text | 12–180 px |
| `font_color` | hex color | text | Text color |
| `background_color` | hex color/null | text | Optional title pill/background |
| `x`, `y` | number | text | Normalized anchor 0–1; centered at that point |
| `fit` | `cover`/`contain` | image/video | Crop-fill or fit-with-padding |
| `volume` | number | audio | Gain 0–2 |
| `fade_in_seconds` / `fade_out_seconds` | number | audio and visual metadata | Fade duration; combined value cannot exceed clip duration |

a clip must end no later than `duration_seconds`. IDs must be unique, track references must exist, and track-kind compatibility is validated before rendering.

## Example

See `examples/timeline.json`. It is a schema example: replace the placeholder asset refs with refs returned by `/v1/assets` or relative asset file paths for CLI use.

## Render limitations in 1.3

- The renderer provides timeline compositing for full-frame visual clips and text overlays. It does not implement interactive transitions, keyframe animation, motion tracking, masking, chroma key, multi-cam editing, or proxy media generation.
- `x` and `y` are applied to text overlays. Visual video/image clips currently fill the composition canvas using `fit`.
- Browser preview should be treated as an editorial preview, not a pixel-identical render guarantee.
- The render endpoint is synchronous and has a bounded in-process semaphore, not a durable distributed queue.
- Browser project state, autosave, undo/redo, and collaborative editing are frontend/backend responsibilities, not implemented in this Python package.
