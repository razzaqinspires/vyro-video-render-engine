from __future__ import annotations

import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    for index, (label, background) in enumerate([
        ("VYRO / FRAME 01", (20, 30, 26)),
        ("VYRO / FRAME 02", (32, 34, 22)),
    ], start=1):
        image = Image.new("RGB", (1080, 1920), background)
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 16, 1920), fill=(184, 255, 0))
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        except OSError:
            font = ImageFont.load_default()
        box = draw.textbbox((0, 0), label, font=font)
        draw.text(((1080 - box[2] + box[0]) // 2, 900), label, fill=(250, 252, 250), font=font)
        image.save(ASSETS / f"frame_{index:02d}.png", optimize=True)

    with wave.open(str(ASSETS / "demo_audio.wav"), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(44100)
        audio.writeframes(b"\x00\x00" * 44100 * 8)

    print(f"Demo media created in {ASSETS}")


if __name__ == "__main__":
    main()
