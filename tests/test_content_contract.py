import pytest
from vyro_video_render_engine.models import ContentPackage


def sample_package():
    return {
        "content_id": "vyro-render-001", "title": "VYRO demo Reel", "duration_seconds": 16,
        "selected_hook": "Mulai dengan satu pesan yang jelas",
        "narration": "Tampilkan visual, jelaskan manfaat yang benar, lalu beri ajakan sederhana.",
        "caption": "Draf demo VYRO MEDIA.",
        "scenes": [
            {"scene_number": 1, "duration_seconds": 8, "visual_direction": "Close-up produk", "on_screen_text": "Satu pesan yang jelas", "visual_prompt": "Cinematic product still"},
            {"scene_number": 2, "duration_seconds": 8, "visual_direction": "Creator berbicara", "on_screen_text": "Tampilkan manfaat", "visual_prompt": "Natural creator portrait"},
        ],
    }


def test_content_id_validation():
    assert ContentPackage.validate_content_id("vyro-render-001") == "vyro-render-001"
    with pytest.raises(ValueError):
        ContentPackage.validate_content_id("../outside")


def test_render_package_defaults_to_review_required():
    package = ContentPackage.model_validate(sample_package())
    assert package.human_review_required is True
    assert package.review_approved is False
    assert package.scenes[0].visual_prompt == "Cinematic product still"
