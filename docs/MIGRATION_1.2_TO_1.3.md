# Migration from 1.2.0 to 1.3.0

## Summary

Version 1.2 rendered approved `ContentPackage` scene sequences. Version 1.3 introduces an explicit multi-track `Timeline` model. The CLI retains a compatibility adapter for existing ContentPackage JSON.

## What changes

- Engine version is `1.3.0`.
- The HTTP `POST /v1/render` request now requires `timeline` and `review_approved` at the request root.
- Asset uploads now validate file signatures, not only extensions.
- Upload support expands to MP4 and MOV video assets.
- Timeline validation enforces unique track/clip IDs, track-kind compatibility, clip boundaries and fade limits.
- Render output is verified with `ffprobe`, then hashed and written to a manifest.
- Human approval is a mandatory server-side gate.

## Compatibility path

Existing JSON `ContentPackage` scripts can still be rendered with:

```bash
vyro-render render-legacy content_package.json --output output/master.mp4 --assets-dir assets
```

The adapter creates one visual track and converts scene text to generated PNG title cards when no image asset is provided. Existing Content Engine integrations should be migrated deliberately; do not assume the HTTP API accepts the legacy shape.

## New integration flow

1. Browser editor serializes current state to Timeline Schema 1.0.
2. Trusted VYRO backend validates the user session, project ownership and review decision.
3. Backend uploads the required asset blobs to `/v1/assets` and maps returned `asset_ref` values into the timeline.
4. Backend calls `/v1/render` with `review_approved: true` after recording the reviewer identity and approval event in its own audit store.
5. Backend saves the render manifest and securely proxies or signs the download response.

The render service's `review_approved` declaration is not a substitute for the Library's member identity, authorization, or audit log.
