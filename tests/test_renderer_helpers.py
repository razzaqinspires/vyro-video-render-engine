from pathlib import Path
from vyro_video_render_engine.renderer import sha256

def test_sha256_is_stable(tmp_path: Path):
    path=tmp_path/"sample.bin"; path.write_bytes(b"vyro")
    assert sha256(path)==sha256(path)


def test_renderer_accepts_content_engine_scene_duration_contract():
    from vyro_video_render_engine.models import Scene
    scene = Scene(scene_number=1, duration_seconds=40, visual_direction="Longer scene for narration", on_screen_text="Long scene")
    assert scene.duration_seconds == 40
