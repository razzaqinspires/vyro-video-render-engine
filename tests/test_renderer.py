import shutil
import wave
from pathlib import Path

import pytest
from PIL import Image

from vyro_video_render_engine.renderer import inspect_video, render_timeline, sha256

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools unavailable")


def make_audio(path: Path, seconds: int = 3):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(44100)
        wav.writeframes(b"\x00\x00" * 44100 * seconds)


def test_render_multitrack_mp4_with_audio(tmp_path: Path):
    assets = tmp_path / "assets"
    assets.mkdir()
    Image.new("RGB", (640, 360), (20, 80, 30)).save(assets / "still.png")
    make_audio(assets / "audio.wav")
    timeline = {
        "title": "Test render", "width": 540, "height": 960, "fps": 24,
        "duration_seconds": 3,
        "tracks": [
            {"track_id": "V1", "name": "Footage", "kind": "video", "order": 0},
            {"track_id": "T1", "name": "Titles", "kind": "overlay", "order": 1},
            {"track_id": "A1", "name": "Audio", "kind": "audio", "order": 2},
        ],
        "clips": [
            {"clip_id": "shot001", "track_id": "V1", "kind": "image", "start_seconds": 0, "duration_seconds": 3, "asset_ref": "still.png"},
            {"clip_id": "title001", "track_id": "T1", "kind": "text", "start_seconds": 0.5, "duration_seconds": 2, "text": "VYRO TEST", "font_size": 54},
            {"clip_id": "audio001", "track_id": "A1", "kind": "audio", "start_seconds": 0, "duration_seconds": 3, "asset_ref": "audio.wav", "fade_in_seconds": 0.2},
        ],
    }
    output = tmp_path / "rendered.mp4"
    manifest = render_timeline(timeline, output, tmp_path / "work", assets, preset="ultrafast", crf=25)
    meta = inspect_video(output)
    assert output.exists() and output.stat().st_size > 1000
    assert meta["has_audio"] is True
    assert meta["width"] == 540 and meta["height"] == 960
    assert abs(meta["duration_seconds"] - 3) < 0.5
    assert manifest["sha256"] == sha256(output)
    assert (tmp_path / "rendered.manifest.json").is_file()


def test_legacy_content_package_adapter_renders(tmp_path: Path):
    from vyro_video_render_engine.renderer import render

    package_path = tmp_path / "content.json"
    package_path.write_text(
        '{"content_id":"legacy-demo-001","title":"Legacy demo",'
        '"duration_seconds":8,"selected_hook":"Legacy","narration":"",'
        '"caption":"","scenes":['
        '{"scene_number":1,"duration_seconds":4,"visual_direction":"Intro","on_screen_text":"First frame"},'
        '{"scene_number":2,"duration_seconds":4,"visual_direction":"Close","on_screen_text":"Second frame"}]}',
        encoding="utf-8",
    )
    output = tmp_path / "legacy.mp4"
    result = render(package_path, output, tmp_path / "legacy-work", tmp_path / "assets")
    assert output.is_file()
    assert result["metadata"]["has_audio"] is False
    assert result["clip_count"] == 2
