from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .models import ContentPackage, Timeline


BLACK = (5, 7, 8)
WHITE = (250, 252, 250)
LIME = (184, 255, 0)
MUTED = (160, 166, 160)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(
            f"FFmpeg command failed ({result.returncode}).\n{result.stderr[-5000:]}"
        )
    return result


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
        "/system/fonts/Roboto-Bold.ttf" if bold else "/system/fonts/Roboto-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def build_frame(
    scene: Any,
    package: Any,
    frame_path: Path,
    index: int,
    total: int,
    asset_path: str | None = None,
    width: int = 1080,
    height: int = 1920,
) -> None:
    """Legacy ContentPackage scene frame builder retained for compatibility."""
    if asset_path:
        source = Path(asset_path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"Asset not found: {source}")
        try:
            with Image.open(source) as opened:
                if opened.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError(f"Unsupported image format: {opened.format}")
                base = opened.convert("RGB")
            ratio = max(width / base.width, height / base.height)
            base = base.resize((max(width, int(base.width * ratio)), max(height, int(base.height * ratio))))
            x = (base.width - width) // 2
            y = (base.height - height) // 2
            image = base.crop((x, y, x + width, y + height))
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 118))
            image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        except Exception as exc:
            raise ValueError(f"Could not load scene asset {source.name}: {exc}") from exc
    else:
        image = Image.new("RGB", (width, height), BLACK)

    draw = ImageDraw.Draw(image)
    draw.polygon([(0, 0), (width, 0), (width, 100), (0, min(360, height // 4))], fill=(12, 16, 16))
    draw.rectangle((0, 0, max(6, width // 54), height), fill=LIME)
    margin = max(44, width // 16)
    draw.rounded_rectangle(
        (margin, margin, width - margin, height - margin),
        radius=max(18, width // 30), outline=(85, 95, 80), width=max(2, width // 360),
    )
    draw.text((margin + 24, margin + 24), "VYRO / CONTENT LAB", font=_font(max(18, width // 34), True), fill=LIME)
    draw.text((margin + 24, margin + 74), f"{index + 1:02d}  /  {total:02d}", font=_font(max(16, width // 44)), fill=MUTED)
    title_font = _font(max(34, width // 15), True)
    lines = _wrap(draw, str(scene.on_screen_text), title_font, width - 2 * (margin + 55))[:8]
    block_h = len(lines) * int(title_font.size * 1.26 if hasattr(title_font, "size") else width // 12)
    y = max(height // 3, min((height - block_h) // 2, height * 2 // 3))
    for line in lines:
        draw.text((margin + 48, y), line, font=title_font, fill=WHITE, stroke_width=1, stroke_fill=(0, 0, 0))
        y += int(title_font.size * 1.26 if hasattr(title_font, "size") else width // 12)
    draw.rounded_rectangle(
        (margin + 30, height - margin - 150, width - margin - 30, height - margin - 50),
        radius=16, fill=(25, 30, 20),
    )
    draw.text((margin + 60, height - margin - 122), "@vyromedia.id", font=_font(max(20, width // 28), True), fill=LIME)
    frame_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(frame_path, format="PNG", optimize=True)


def _verify_asset(asset_root: Path, ref: str, expected_kind: str) -> Path:
    if not ref or Path(ref).is_absolute() or ".." in Path(ref).parts:
        raise ValueError("Invalid asset reference")
    root = asset_root.resolve()
    path = (root / ref).resolve()
    if root not in path.parents or not path.is_file():
        raise FileNotFoundError(f"Timeline asset not found: {ref}")
    extension = path.suffix.lower()
    allowed = {
        "image": {".png", ".jpg", ".jpeg", ".webp"},
        "video": {".mp4", ".mov", ".webm"},
        "audio": {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"},
    }
    if extension not in allowed[expected_kind]:
        raise ValueError(f"Asset extension {extension} is not valid for {expected_kind}")
    return path


def _text_frame(clip: Any, width: int, height: int, target: Path) -> None:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _font(clip.font_size, True)
    color = clip.font_color
    lines = _wrap(draw, clip.text or "", font, int(width * 0.84))[:8]
    line_heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
    total_h = sum(line_heights) + max(0, len(lines) - 1) * int(clip.font_size * 0.18)
    center_x = int(width * clip.x)
    center_y = int(height * clip.y)
    y = center_y - total_h // 2
    if clip.background_color:
        pad_x, pad_y = int(clip.font_size * 0.36), int(clip.font_size * 0.24)
        draw.rounded_rectangle(
            (center_x - int(width * 0.43), y - pad_y,
             center_x + int(width * 0.43), y + total_h + pad_y),
            radius=max(8, int(clip.font_size * 0.2)), fill=clip.background_color,
        )
    for line, line_h in zip(lines, line_heights, strict=True):
        bbox = draw.textbbox((0, 0), line, font=font)
        x = center_x - (bbox[2] - bbox[0]) // 2
        draw.text((x, y), line, font=font, fill=color, stroke_width=1, stroke_fill=(0, 0, 0, 90))
        y += line_h + int(clip.font_size * 0.18)
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, format="PNG", optimize=True)


def _escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_timeline(
    timeline_data: Timeline | dict[str, Any],
    output: Path,
    workdir: Path,
    assets_dir: Path,
    preset: str = "medium",
    crf: int = 20,
) -> dict[str, Any]:
    """Render an editable multi-track timeline to an H.264/AAC MP4 master."""
    timeline = timeline_data if isinstance(timeline_data, Timeline) else Timeline.model_validate(timeline_data)
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg tidak ditemukan di PATH")
    if preset not in {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower"}:
        raise ValueError("Unsupported FFmpeg preset")
    if not 15 <= crf <= 28:
        raise ValueError("CRF must be between 15 and 28")

    output = output.expanduser().resolve()
    workdir = workdir.expanduser().resolve()
    assets_dir = assets_dir.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    workdir.mkdir(parents=True, exist_ok=True)

    active = [clip for clip in timeline.clips if clip.enabled]
    tracks = {track.track_id: track for track in timeline.tracks}
    track_order = {track.track_id: track.order for track in timeline.tracks}
    visual = sorted(
        [c for c in active if c.kind in {"video", "image", "text"}],
        key=lambda c: (track_order[c.track_id], c.start_seconds, c.clip_id),
    )
    audio = [c for c in active if c.kind == "audio" and not tracks[c.track_id].muted]
    if len(visual) + len(audio) > 80:
        raise ValueError("Timeline has too many active clips")

    inputs: list[str] = [
        "-f", "lavfi", "-i",
        f"color=c={timeline.background_color}:s={timeline.width}x{timeline.height}:r={timeline.fps}:d={timeline.duration_seconds:.3f}",
    ]
    clip_input: dict[str, int] = {}
    generated_text: list[Path] = []
    input_index = 1
    for clip in visual + audio:
        if clip.kind == "text":
            text_path = workdir / f"text_{clip.clip_id}.png"
            _text_frame(clip, timeline.width, timeline.height, text_path)
            generated_text.append(text_path)
            inputs += ["-loop", "1", "-framerate", str(timeline.fps), "-t", f"{clip.duration_seconds:.3f}", "-i", str(text_path)]
        else:
            media_kind = "audio" if clip.kind == "audio" else clip.kind
            path = _verify_asset(assets_dir, clip.asset_ref or "", media_kind)
            if clip.kind == "image":
                inputs += ["-loop", "1", "-framerate", str(timeline.fps), "-t", f"{clip.duration_seconds:.3f}", "-i", str(path)]
            elif clip.kind == "video":
                inputs += ["-ss", f"{clip.source_in_seconds:.3f}", "-t", f"{clip.duration_seconds:.3f}", "-i", str(path)]
            else:
                inputs += ["-ss", f"{clip.source_in_seconds:.3f}", "-t", f"{clip.duration_seconds:.3f}", "-i", str(path)]
        clip_input[clip.clip_id] = input_index
        input_index += 1

    filters: list[str] = []
    filters: list[str] = ["[0:v]setpts=PTS-STARTPTS[base0]"]
    current = "base0"
    for position, clip in enumerate(visual, start=1):
        idx = clip_input[clip.clip_id]
        end = clip.start_seconds + clip.duration_seconds
        if clip.kind == "video":
            source_filter = f"[{idx}:v]trim=duration={clip.duration_seconds:.3f},setpts=PTS-STARTPTS"
        else:
            source_filter = f"[{idx}:v]trim=duration={clip.duration_seconds:.3f},setpts=PTS-STARTPTS"
        if clip.fit == "cover":
            fit_filter = (
                f"scale={timeline.width}:{timeline.height}:force_original_aspect_ratio=increase,"
                f"crop={timeline.width}:{timeline.height}"
            )
        else:
            fit_filter = (
                f"scale={timeline.width}:{timeline.height}:force_original_aspect_ratio=decrease,"
                f"pad={timeline.width}:{timeline.height}:(ow-iw)/2:(oh-ih)/2:color=black@0"
            )
        layer_filters = [fit_filter, f"setsar=1", f"fps={timeline.fps}", "format=rgba"]
        if clip.fade_in_seconds:
            layer_filters.append(f"fade=t=in:st=0:d={clip.fade_in_seconds:.3f}:alpha=1")
        if clip.fade_out_seconds:
            fade_start = max(0.0, clip.duration_seconds - clip.fade_out_seconds)
            layer_filters.append(
                f"fade=t=out:st={fade_start:.3f}:d={clip.fade_out_seconds:.3f}:alpha=1"
            )
        layer_filters.append(f"setpts=PTS+{clip.start_seconds:.3f}/TB")
        filters.append(source_filter + "," + ",".join(layer_filters) + f"[v{position}]")
        out_label = f"mix{position}"
        filters.append(
            f"[{current}][v{position}]overlay=0:0:enable='between(t,{clip.start_seconds:.3f},{end:.3f})':"
            f"eof_action=pass:shortest=0:format=auto[{out_label}]"
        )
        current = out_label

    filters.append(f"[{current}]trim=duration={timeline.duration_seconds:.3f},setpts=PTS-STARTPTS,format=yuv420p[vout]")
    audio_labels: list[str] = []
    for position, clip in enumerate(audio):
        idx = clip_input[clip.clip_id]
        label = f"a{position}"
        delay_ms = round(clip.start_seconds * 1000)
        filters.append(
            f"[{idx}:a]atrim=duration={clip.duration_seconds:.3f},asetpts=PTS-STARTPTS,"
            f"volume={clip.volume:.3f},"
            f"afade=t=in:st=0:d={clip.fade_in_seconds:.3f},"
            f"afade=t=out:st={max(0, clip.duration_seconds - clip.fade_out_seconds):.3f}:d={clip.fade_out_seconds:.3f},"
            f"adelay={delay_ms}:all=1[{label}]"
        )
        audio_labels.append(label)

    graph = list(filters)
    if audio_labels:
        if len(audio_labels) == 1:
            audio_graph = f"[{audio_labels[0]}]apad,atrim=duration={timeline.duration_seconds:.3f}[aout]"
        else:
            joined = "".join(f"[{label}]" for label in audio_labels)
            audio_graph = (
                f"{joined}amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=0,"
                f"apad,atrim=duration={timeline.duration_seconds:.3f}[aout]"
            )
        graph.append(audio_graph)

    command = ["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex", ";".join(graph),
               "-map", "[vout]"]
    if audio_labels:
        command += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    else:
        command += ["-an"]
    command += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-r", str(timeline.fps),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-t", f"{timeline.duration_seconds:.3f}", str(output)]
    _run(command)
    metadata = inspect_video(output)
    if abs(float(metadata["duration_seconds"]) - timeline.duration_seconds) > 0.5:
        raise RuntimeError(
            f"Rendered duration mismatch: expected {timeline.duration_seconds:.3f}s, "
            f"got {metadata['duration_seconds']:.3f}s"
        )
    manifest: dict[str, Any] = {
        "engine_version": "1.3.0", "title": timeline.title, "output": str(output),
        "sha256": sha256(output), "metadata": metadata,
        "clip_count": len(active), "track_count": len(timeline.tracks),
        "human_review_required": True,
        "timeline_schema_version": timeline.schema_version,
        "clips": [clip.model_dump(mode="json") for clip in active],
    }
    output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def inspect_video(path: Path) -> dict[str, Any]:
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe tidak ditemukan di PATH")
    if not path.is_file():
        raise FileNotFoundError(path)
    result = _run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], 60)
    metadata = json.loads(result.stdout)
    video = next((stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "video"), None)
    if not video:
        raise ValueError("Output tidak memiliki video stream")
    duration = float(metadata.get("format", {}).get("duration", 0))
    if duration < 1:
        raise ValueError("Durasi output tidak valid")
    return {
        "width": int(video.get("width", 0)), "height": int(video.get("height", 0)),
        "duration_seconds": duration, "video_codec": video.get("codec_name"),
        "audio_codec": next((s.get("codec_name") for s in metadata.get("streams", []) if s.get("codec_type") == "audio"), None),
        "has_audio": any(s.get("codec_type") == "audio" for s in metadata.get("streams", [])),
        "fps": video.get("r_frame_rate"),
    }


def render(
    content_json: Path,
    output: Path,
    workdir: Path,
    assets_dir: Path | None = None,
    voiceover: Path | None = None,
) -> dict[str, Any]:
    """Render legacy ContentPackage JSON, preserving v1.2 integration compatibility."""
    package = ContentPackage.model_validate_json(content_json.read_text(encoding="utf-8"))
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg tidak ditemukan di PATH")
    assets_root = (assets_dir or Path(".")).resolve()
    generated_root = assets_root / ".legacy_generated"
    generated_root.mkdir(parents=True, exist_ok=True)
    tracks = [
        {"track_id": "V1", "name": "Scene visuals", "kind": "video", "order": 0},
    ]
    clips: list[dict[str, Any]] = []
    cursor = 0.0
    for index, scene in enumerate(package.scenes):
        duration = float(scene.duration_seconds)
        if scene.asset_hint:
            if assets_dir is None:
                raise ValueError("Scene has asset_hint but --assets-dir was not supplied")
            asset_path = Path(scene.asset_hint)
            if asset_path.is_absolute() or ".." in asset_path.parts:
                raise ValueError("Asset path escapes assets directory")
            candidate = (assets_root / asset_path).resolve()
            if assets_root not in candidate.parents or not candidate.is_file():
                raise FileNotFoundError(f"Asset not found: {scene.asset_hint}")
            asset_ref = str(candidate.relative_to(assets_root))
        else:
            generated = generated_root / f"scene_{index + 1:02d}.png"
            image = Image.new("RGB", (1080, 1920), BLACK)
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, 18, 1920), fill=LIME)
            font = _font(76, True)
            lines = _wrap(draw, scene.on_screen_text, font, 900)[:8]
            line_height = 100
            y = (1920 - len(lines) * line_height) // 2
            for line in lines:
                box = draw.textbbox((0, 0), line, font=font)
                draw.text(((1080 - (box[2] - box[0])) // 2, y), line, font=font, fill=WHITE)
                y += line_height
            image.save(generated, format="PNG", optimize=True)
            asset_ref = str(generated.relative_to(assets_root))
        clips.append({
            "clip_id": f"scene_{index + 1}", "track_id": "V1", "kind": "image",
            "start_seconds": cursor, "duration_seconds": duration, "asset_ref": asset_ref,
        })
        cursor += duration
    total = max(float(package.duration_seconds), cursor)
    timeline_tracks = list(tracks)
    if voiceover:
        voice_path = Path(voiceover).resolve()
        voice_copy = generated_root / f"voiceover{voice_path.suffix.lower()}"
        if voice_path != voice_copy:
            shutil.copy2(voice_path, voice_copy)
        timeline_tracks.append({"track_id": "A1", "name": "Voiceover", "kind": "audio", "order": 1})
        clips.append({
            "clip_id": "legacy_voiceover", "track_id": "A1", "kind": "audio",
            "start_seconds": 0, "duration_seconds": total,
            "asset_ref": str(voice_copy.relative_to(assets_root)),
        })
    timeline = {
        "title": package.title, "width": 1080, "height": 1920, "fps": 30,
        "duration_seconds": total, "tracks": timeline_tracks, "clips": clips,
    }
    return render_timeline(timeline, output, workdir, assets_root)
