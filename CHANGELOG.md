# Changelog

## 1.3.0 — Multi-track timeline rendering
- Added strict Timeline Schema 1.0 and visual/audio track contracts.
- Added layered video, image and title compositing with multi-source audio mix.
- Added timeline clip placement, source trim, fit mode, audio gain, audio fades and optional visual alpha fades.
- Added file-signature validation for image, audio and video media.
- Added `ffprobe` output verification and SHA-256 render manifest.
- Added explicit API review approval, bounded render concurrency and configurable timeline limits.
- Added editor integration, API and migration documentation.
- Retained ContentPackage compatibility through `vyro-render render-legacy`.

## 1.2.0 — Demo-isolated rendering
- Added demo-ID namespacing for uploaded image/audio assets and rendered MP4 outputs.
- Added asset ownership sidecars, path validation, and automatic TTL cleanup.
- Aligned render scene models with Content Engine v1.3 visual prompt fields.
- Preserved explicit human approval requirement for final render.
