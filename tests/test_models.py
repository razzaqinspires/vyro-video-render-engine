import pytest
from pydantic import ValidationError

from vyro_video_render_engine.models import ContentPackage, Timeline


def valid_timeline():
    return {
        "title": "Test",
        "duration_seconds": 8,
        "tracks": [
            {"track_id": "V1", "name": "Video", "kind": "video", "order": 0},
            {"track_id": "T1", "name": "Titles", "kind": "overlay", "order": 1},
            {"track_id": "A1", "name": "Audio", "kind": "audio", "order": 2},
        ],
        "clips": [
            {"clip_id": "clip001", "track_id": "V1", "kind": "image", "start_seconds": 0, "duration_seconds": 8, "asset_ref": "demo/file.png"},
            {"clip_id": "title01", "track_id": "T1", "kind": "text", "start_seconds": 1, "duration_seconds": 3, "text": "VYRO"},
        ],
    }


def test_valid_timeline_contract():
    timeline = Timeline.model_validate(valid_timeline())
    assert timeline.fps == 30
    assert len(timeline.clips) == 2


def test_reject_duplicate_clip_ids():
    payload = valid_timeline()
    payload["clips"].append({**payload["clips"][0], "track_id": "V1"})
    with pytest.raises(ValidationError):
        Timeline.model_validate(payload)


def test_reject_clip_beyond_project_duration():
    payload = valid_timeline()
    payload["clips"][0]["start_seconds"] = 2
    with pytest.raises(ValidationError):
        Timeline.model_validate(payload)


def test_audio_track_only_accepts_audio():
    payload = valid_timeline()
    payload["clips"].append({"clip_id": "badclip", "track_id": "A1", "kind": "image", "start_seconds": 0, "duration_seconds": 2, "asset_ref": "demo/a.png"})
    with pytest.raises(ValidationError):
        Timeline.model_validate(payload)


def test_text_clip_requires_text():
    payload = valid_timeline()
    payload["clips"].append({"clip_id": "badclip", "track_id": "T1", "kind": "text", "start_seconds": 0, "duration_seconds": 2})
    with pytest.raises(ValidationError):
        Timeline.model_validate(payload)


def test_content_package_compatibility():
    package = ContentPackage.model_validate({
        "content_id": "vyro-demo-001", "title": "Demo", "duration_seconds": 16,
        "selected_hook": "Hook", "narration": "Narration", "caption": "Caption",
        "scenes": [
            {"scene_number": 1, "duration_seconds": 8, "visual_direction": "Opening", "on_screen_text": "First"},
            {"scene_number": 2, "duration_seconds": 8, "visual_direction": "Close", "on_screen_text": "Second"},
        ],
    })
    assert package.human_review_required is True
    assert package.review_approved is False


def test_reject_legacy_package_scene_sum_over_duration():
    with pytest.raises(ValidationError):
        ContentPackage.model_validate({
            "content_id": "vyro-demo-001", "title": "Demo", "duration_seconds": 8,
            "selected_hook": "Hook", "scenes": [
                {"scene_number": 1, "duration_seconds": 8, "visual_direction": "Opening", "on_screen_text": "First"},
                {"scene_number": 2, "duration_seconds": 8, "visual_direction": "Close", "on_screen_text": "Second"},
            ],
        })
