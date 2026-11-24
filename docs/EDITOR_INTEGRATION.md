# VYRO MEDIA Editor Integration Contract

This engine is intentionally separate from the editing UI. `/editor.html` or a future VYRO MEDIA Studio application should own the editing experience and pass a stable timeline contract to the trusted server adapter.

## Expected editor responsibilities

- Media bin: local import, metadata extraction, thumbnails, duplicate detection and project-level media references.
- Timeline: tracks, clip selection, drag/trim/split, snapping, zoom, markers, audio waveform, text overlays and layer ordering.
- Preview: browser playback and canvas composition. Treat preview as an approximate editorial view; final codec/render timing is authoritative from FFmpeg.
- Project safety: autosave, version history, undo/redo, import/export project JSON and recoverable drafts.
- Review: explicit human approval, recorded reviewer, timestamp and change state before final render.
- Render lifecycle: upload assets, serialize timeline, submit final render, poll or await server response, display failure details, download master and keep manifest with project.

## Service boundary

A browser must never hold `VYRO_SERVICE_API_KEY`. Use a server route or private backend adapter:

```text
Browser Editor
  -> POST /api/vyro/render (member session + CSRF protection)
     -> validate user/project ownership + review state
     -> upload assets to private render service
     -> call VYRO_RENDER_API_URL/v1/render with service credential
     <- store render manifest + access policy
  <- provide authorized progress/result and download URL
```

## Browser prototype vs final renderer

Use `HTMLVideoElement`, `HTMLAudioElement`, Canvas/WebGL and Web Audio API for responsive preview. Use the Python FFmpeg engine for consistent MP4 export. Do not treat a browser-side WebM recording as the final MP4 master. Expensive work should move to a durable worker queue when concurrent production usage is introduced.

## Not implemented by this engine

Interactive timeline editing, project database, browser autosave, multi-user collaboration, AI generation, AI voice cloning, publishing or social scheduling are intentionally separate concerns.
