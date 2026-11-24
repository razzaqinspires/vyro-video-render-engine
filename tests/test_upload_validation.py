from vyro_video_render_engine.upload_validation import safe_display_filename, validate_asset_signature


def test_validates_png_signature():
    assert validate_asset_signature(".png", b"\x89PNG\r\n\x1a\n" + b"x" * 20)


def test_rejects_mismatched_image_signature():
    assert not validate_asset_signature(".png", b"ID3" + b"x" * 20)


def test_validates_webp_signature():
    assert validate_asset_signature(".webp", b"RIFF" + b"abcd" + b"WEBP" + b"data")


def test_validates_mp4_signature():
    assert validate_asset_signature(".mp4", b"\x00\x00\x00\x18ftypisom" + b"x" * 20)


def test_safe_filename_strips_path():
    assert safe_display_filename("../../unsafe/file.png") == "file.png"
