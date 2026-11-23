from pathlib import Path
from vyro_video_render_engine.renderer import sha256

def test_sha256_is_stable(tmp_path: Path):
    path=tmp_path/"sample.bin"; path.write_bytes(b"vyro")
    assert sha256(path)==sha256(path)
