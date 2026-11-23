from __future__ import annotations


def validate_asset_signature(suffix: str, data: bytes) -> bool:
    suffix = suffix.lower()
    signatures = {
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": data.startswith(b"\xff\xd8\xff"),
        ".jpeg": data.startswith(b"\xff\xd8\xff"),
        ".webp": len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP",
        ".wav": len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WAVE",
        ".mp3": data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0),
        ".m4a": len(data) >= 12 and data[4:8] == b"ftyp",
    }
    return bool(signatures.get(suffix, False))
