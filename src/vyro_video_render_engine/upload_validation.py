from __future__ import annotations

from pathlib import Path


_SIGNATURES = {
    ".png": lambda d: d.startswith(b"\x89PNG\r\n\x1a\n"),
    ".jpg": lambda d: d.startswith(b"\xff\xd8\xff"),
    ".jpeg": lambda d: d.startswith(b"\xff\xd8\xff"),
    ".webp": lambda d: len(d) >= 12 and d[:4] == b"RIFF" and d[8:12] == b"WEBP",
    ".wav": lambda d: len(d) >= 12 and d[:4] == b"RIFF" and d[8:12] == b"WAVE",
    ".mp3": lambda d: d.startswith(b"ID3") or (len(d) >= 2 and d[0] == 0xFF and (d[1] & 0xE0) == 0xE0),
    ".m4a": lambda d: len(d) >= 12 and d[4:8] == b"ftyp",
    ".mp4": lambda d: len(d) >= 12 and d[4:8] == b"ftyp",
    ".mov": lambda d: len(d) >= 12 and d[4:8] == b"ftyp",
}


def validate_asset_signature(suffix: str, data: bytes) -> bool:
    validator = _SIGNATURES.get(suffix.lower())
    return bool(validator and validator(data))


def safe_display_filename(filename: str) -> str:
    """Return a display-only basename; never use the user filename as a storage path."""
    return Path(filename.replace("\\", "/")).name[:180]
