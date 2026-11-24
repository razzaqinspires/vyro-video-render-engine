# Engine Test Report — 24 November 2026

## Automated tests

- `pytest -q`: **18 passed**.
- `python -m compileall -q src tests`: passed.
- Full sample CLI render: passed.
- `ffprobe` output inspection: passed.

## Sample render evidence

Executed:

```bash
PYTHONPATH=src python -m vyro_video_render_engine.cli render \
  examples/timeline.demo.json \
  --output /tmp/vyro-engine-demo.mp4 \
  --assets-dir assets \
  --preset ultrafast \
  --crf 24

PYTHONPATH=src python -m vyro_video_render_engine.cli inspect /tmp/vyro-engine-demo.mp4
```

Verified output:

- Video codec: H.264
- Audio codec: AAC
- Dimensions: 720 × 1280
- Frame rate: 30 FPS
- Duration: 8.0 seconds
- Audio stream present: yes
- Timeline: 5 clips across 3 tracks
- Render manifest includes SHA-256

## Tooling note

Ruff was not installed in the execution environment, so Ruff lint/format checks were not run. Python compile checks and runtime tests were run. No production deployment or external provider inference was attempted.
