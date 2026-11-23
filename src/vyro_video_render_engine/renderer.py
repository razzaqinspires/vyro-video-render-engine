from __future__ import annotations
import hashlib, json, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .models import ContentPackage

W, H = 1080, 1920
BLACK=(5,7,8); WHITE=(250,252,250); LIME=(184,255,0); MUTED=(160,166,160)

def _font(size: int, bold: bool=False):
    options = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/system/fonts/Roboto-Bold.ttf" if bold else "/system/fonts/Roboto-Regular.ttf",
    ]
    for candidate in options:
        if Path(candidate).exists(): return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()

def _wrap(draw, text, font, max_width):
    words=text.split(); lines=[]; current=""
    for word in words:
        candidate=f"{current} {word}".strip()
        if draw.textbbox((0,0),candidate,font=font)[2] <= max_width: current=candidate
        else:
            if current: lines.append(current)
            current=word
    if current: lines.append(current)
    return lines

def build_frame(scene, package, frame_path: Path, index: int, total: int, asset_path: str|None=None):
    if asset_path:
        source=Path(asset_path).expanduser().resolve()
        if not source.is_file(): raise FileNotFoundError(f"Asset not found: {source}")
        try:
            with Image.open(source) as opened:
                if opened.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ValueError(f"Unsupported image format: {opened.format}")
                base=opened.convert("RGB")
            # Cover crop; overlays keep readable contrast.
            ratio=max(W/base.width,H/base.height)
            base=base.resize((int(base.width*ratio),int(base.height*ratio)))
            x=(base.width-W)//2; y=(base.height-H)//2
            img=base.crop((x,y,x+W,y+H))
            overlay=Image.new("RGBA",(W,H),(0,0,0,125))
            img=Image.alpha_composite(img.convert("RGBA"),overlay).convert("RGB")
        except Exception as exc:
            raise ValueError(f"Could not load scene asset {source.name}: {exc}") from exc
    else:
        img=Image.new("RGB",(W,H),BLACK)
    d=ImageDraw.Draw(img)
    d.polygon([(0,0),(W,0),(W,100),(0,360)],fill=(12,16,16))
    d.polygon([(0,H-220),(W,H-430),(W,H),(0,H)],fill=(10,12,12))
    d.rectangle((0,0,20,H),fill=LIME)
    d.rounded_rectangle((64,80,1016,1840),radius=36,outline=(85,95,80),width=3)
    d.text((100,120),"VYRO / CONTENT LAB",font=_font(32,True),fill=LIME)
    d.text((100,178),f"{index+1:02d}  /  {total:02d}",font=_font(25),fill=MUTED)
    title_font=_font(74,True)
    lines=_wrap(d,scene.on_screen_text,title_font,820)
    block_h=len(lines)*102
    y=max(520,min(1040,(H-block_h)//2))
    for line in lines[:8]:
        d.text((110,y),line,font=title_font,fill=WHITE,stroke_width=1,stroke_fill=(0,0,0)); y+=102
    d.rounded_rectangle((100,1635,980,1745),radius=20,fill=(25,30,20))
    d.text((130,1665),"@vyromedia.id",font=_font(38,True),fill=LIME)
    frame_path.parent.mkdir(parents=True,exist_ok=True)
    img.save(frame_path,format="PNG",optimize=True)

def sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""): digest.update(chunk)
    return digest.hexdigest()

def _run(command: list[str], timeout: int=900):
    result=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command[:5])}\n{result.stderr[-4000:]}")
    return result

def inspect_video(path: Path) -> dict:
    if not shutil.which("ffprobe"): raise RuntimeError("ffprobe tidak ditemukan di PATH")
    result=_run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],timeout=60)
    meta=json.loads(result.stdout)
    video=next((s for s in meta.get("streams",[]) if s.get("codec_type")=="video"),None)
    if not video: raise ValueError("Output tidak memiliki video stream")
    if int(video.get("width",0)) != W or int(video.get("height",0)) != H:
        raise ValueError("Output harus tepat 1080x1920")
    duration=float(meta.get("format",{}).get("duration",0))
    if duration < 1: raise ValueError("Durasi output tidak valid")
    return {"width":W,"height":H,"duration_seconds":duration,"video_codec":video.get("codec_name"),"has_audio":any(s.get("codec_type")=="audio" for s in meta.get("streams",[]))}

def render(content_json: Path, output: Path, workdir: Path, assets_dir: Path|None=None, voiceover: Path|None=None) -> dict:
    package=ContentPackage.model_validate_json(content_json.read_text(encoding="utf-8"))
    if not shutil.which("ffmpeg"): raise RuntimeError("ffmpeg tidak ditemukan di PATH")
    if voiceover and not voiceover.is_file(): raise FileNotFoundError(voiceover)
    workdir.mkdir(parents=True,exist_ok=True); output.parent.mkdir(parents=True,exist_ok=True)
    frame_paths=[]; concat=workdir/"frames.ffconcat"; lines=["ffconcat version 1.0"]
    for idx,scene in enumerate(package.scenes):
        frame=workdir/f"scene_{idx+1:02d}.png"
        asset=None
        if scene.asset_hint:
            if assets_dir is None:
                raise ValueError("Scene has asset_hint but --assets-dir was not supplied")
            candidate=(assets_dir/scene.asset_hint).resolve()
            if assets_dir.resolve() not in candidate.parents and candidate != assets_dir.resolve():
                raise ValueError("Asset path escapes assets directory")
            asset=str(candidate)
        build_frame(scene,package,frame,idx,len(package.scenes),asset)
        frame_paths.append(frame)
        lines.extend([f"file '{frame.name}'",f"duration {scene.duration_seconds:.3f}"])
    lines.append(f"file '{frame_paths[-1].name}'")
    concat.write_text("\n".join(lines)+"\n",encoding="utf-8")
    scene_total=sum(float(scene.duration_seconds) for scene in package.scenes)
    command=["ffmpeg","-hide_banner","-y","-safe","0","-f","concat","-i",str(concat),"-t",f"{scene_total:.3f}","-vf","fps=30,scale=1080:1920,format=yuv420p","-c:v","libx264","-preset","medium","-crf","20","-movflags","+faststart"]
    if voiceover:
        command += ["-i",str(voiceover),"-map","0:v:0","-map","1:a:0","-c:a","aac","-b:a","192k","-af","apad","-shortest"]
    else:
        command += ["-an"]
    command += [str(output)]
    _run(command)
    metadata=inspect_video(output)
    if abs(float(metadata["duration_seconds"])-scene_total) > 0.35:
        raise RuntimeError(f"Rendered duration mismatch: expected {scene_total:.3f}s, got {metadata['duration_seconds']:.3f}s")
    manifest={"content_id":package.content_id,"output":str(output.resolve()),"sha256":sha256(output),"metadata":metadata,"frame_count":len(frame_paths),"human_review_required":True,"caption":package.caption}
    output.with_suffix(".manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    return manifest
