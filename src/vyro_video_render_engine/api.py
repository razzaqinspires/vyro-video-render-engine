from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import shutil
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from .models import Timeline
from .renderer import render_timeline
from .upload_validation import safe_display_filename, validate_asset_signature

APP_VERSION = "1.3.0"
app = FastAPI(
    title="VYRO Video Render Engine",
    version=APP_VERSION,
    description="Rights-aware multi-track timeline renderer for VYRO MEDIA.",
    docs_url="/docs",
    redoc_url="/redoc",
)
ASSETS_DIR = Path(os.getenv("VYRO_RENDER_ASSETS_DIR", "./api_assets")).expanduser().resolve()
RENDERS_DIR = Path(os.getenv("VYRO_RENDER_OUTPUT_DIR", "./api_renders")).expanduser().resolve()
MAX_ASSET_BYTES = max(1024 * 1024, min(int(os.getenv("VYRO_RENDER_MAX_ASSET_BYTES", str(20 * 1024 * 1024))), 50 * 1024 * 1024))
ASSET_TTL_HOURS = max(1, min(int(os.getenv("VYRO_RENDER_ASSET_TTL_HOURS", "48")), 720))
RENDER_TTL_HOURS = max(1, min(int(os.getenv("VYRO_RENDER_OUTPUT_TTL_HOURS", "72")), 720))
MAX_TIMELINE_SECONDS = max(1, min(int(os.getenv("VYRO_RENDER_MAX_TIMELINE_SECONDS", "180")), 600))
MAX_CLIPS = max(1, min(int(os.getenv("VYRO_RENDER_MAX_CLIPS", "80")), 120))
RENDER_LOCK = threading.BoundedSemaphore(max(1, min(int(os.getenv("VYRO_RENDER_MAX_CONCURRENT_JOBS", "1")), 4)))
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".m4a", ".mp4", ".mov"}


class AssetUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=180)
    data_base64: str = Field(min_length=16, max_length=70_000_000)


class TimelineRenderRequest(BaseModel):
    timeline: dict[str, Any]
    review_approved: bool = False
    review_note: str | None = Field(default=None, max_length=1000)
    output_preset: str = Field(default="medium", pattern=r"^(ultrafast|superfast|veryfast|faster|fast|medium|slow|slower)$")
    output_crf: int = Field(default=20, ge=15, le=28)


def require_service_key(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("VYRO_SERVICE_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Service API key belum dikonfigurasi")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def demo_namespace(demo_id: str) -> str:
    if not re.fullmatch(r"VYRO-DEMO-[A-Fa-f0-9]{8,40}", demo_id):
        raise HTTPException(status_code=400, detail="Demo ID tidak valid")
    return hashlib.sha256(demo_id.upper().encode()).hexdigest()[:24]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(created_at: str, ttl_hours: int) -> bool:
    created = datetime.fromisoformat(created_at)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return _now() - created > timedelta(hours=ttl_hours)


def cleanup_expired() -> None:
    if ASSETS_DIR.exists():
        for metadata_path in ASSETS_DIR.glob("*/*.meta.json"):
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                if _is_expired(metadata["created_at"], ASSET_TTL_HOURS):
                    asset = metadata_path.with_name(metadata_path.name.removesuffix(".meta.json"))
                    asset.unlink(missing_ok=True)
                    metadata_path.unlink(missing_ok=True)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
    if RENDERS_DIR.exists():
        for folder in RENDERS_DIR.iterdir():
            if not folder.is_dir():
                continue
            try:
                access_path = folder / "access.json"
                data = json.loads(access_path.read_text(encoding="utf-8"))
                if _is_expired(data["created_at"], RENDER_TTL_HOURS):
                    shutil.rmtree(folder, ignore_errors=True)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue


def _resolve_demo_asset(ref: str, namespace: str, expected_kind: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{24}/[a-f0-9]{32}\.[a-z0-9]+", ref):
        raise HTTPException(status_code=422, detail="Asset reference format tidak valid")
    if not ref.startswith(namespace + "/"):
        raise HTTPException(status_code=403, detail="Asset bukan milik demo ini")
    root = ASSETS_DIR.resolve()
    candidate = (root / ref).resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Asset tidak ditemukan")
    metadata_path = candidate.with_name(candidate.name + ".meta.json")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=403, detail="Asset metadata tidak valid") from exc
    if metadata.get("demo_namespace") != namespace:
        raise HTTPException(status_code=403, detail="Hak akses asset tidak valid")
    allowed = {
        "image": {".png", ".jpg", ".jpeg", ".webp"},
        "video": {".mp4", ".mov"},
        "audio": {".wav", ".mp3", ".m4a"},
    }
    if candidate.suffix.lower() not in allowed[expected_kind]:
        raise HTTPException(status_code=415, detail=f"Format asset tidak didukung untuk {expected_kind}")
    return candidate


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "vyro-video-render-engine", "status": "ok", "version": APP_VERSION, "renderer": "ffmpeg"}


@app.post("/v1/assets", dependencies=[Depends(require_service_key)])
def upload_asset(payload: AssetUpload, x_vyro_demo_id: str = Header(default="")) -> dict[str, Any]:
    cleanup_expired()
    namespace = demo_namespace(x_vyro_demo_id)
    display_name = safe_display_filename(payload.filename)
    suffix = Path(display_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Format aset tidak didukung")
    try:
        data = base64.b64decode(payload.data_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Base64 tidak valid") from exc
    if not data or len(data) > MAX_ASSET_BYTES:
        raise HTTPException(status_code=413, detail="Ukuran aset melewati batas layanan")
    if not validate_asset_signature(suffix, data):
        raise HTTPException(status_code=415, detail="Signature file tidak sesuai dengan ekstensi")
    folder = ASSETS_DIR / namespace
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = folder / filename
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(target)
    metadata = {
        "asset_ref": f"{namespace}/{filename}", "demo_namespace": namespace,
        "original_filename": display_name, "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "created_at": _now().isoformat(),
    }
    target.with_name(target.name + ".meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "asset_ref": metadata["asset_ref"], "bytes": len(data),
        "media_type": suffix.lstrip("."), "sha256": metadata["sha256"],
        "expires_after_hours": ASSET_TTL_HOURS,
    }


@app.post("/v1/render", dependencies=[Depends(require_service_key)])
def render_timeline_endpoint(
    payload: TimelineRenderRequest,
    x_vyro_demo_id: str = Header(default=""),
) -> dict[str, Any]:
    cleanup_expired()
    namespace = demo_namespace(x_vyro_demo_id)
    if payload.review_approved is not True:
        raise HTTPException(status_code=409, detail="Persetujuan manusia wajib diberikan sebelum render final")
    try:
        timeline = Timeline.model_validate(payload.timeline)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc
    if timeline.duration_seconds > MAX_TIMELINE_SECONDS or len(timeline.clips) > MAX_CLIPS:
        raise HTTPException(status_code=413, detail="Timeline melewati batas layanan")
    for clip in timeline.clips:
        if not clip.enabled or clip.kind == "text":
            continue
        _resolve_demo_asset(clip.asset_ref or "", namespace, clip.kind)

    if not RENDER_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="Render queue sedang penuh; coba kembali")
    render_id = uuid.uuid4().hex
    job_dir = RENDERS_DIR / render_id
    try:
        job_dir.mkdir(parents=True, exist_ok=False)
        manifest = render_timeline(
            timeline, job_dir / "master.mp4", job_dir / "work", ASSETS_DIR,
            preset=payload.output_preset, crf=payload.output_crf,
        )
        access = {
            "render_id": render_id, "demo_namespace": namespace,
            "review_approved": True, "review_note": payload.review_note,
            "created_at": _now().isoformat(),
        }
        (job_dir / "access.json").write_text(json.dumps(access, indent=2), encoding="utf-8")
    except (RuntimeError, ValueError, FileNotFoundError, OSError) as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        RENDER_LOCK.release()
    return {
        "render_id": render_id, "status": "rendered", "manifest": manifest,
        "download_url": f"/v1/renders/{render_id}/download",
        "human_review_required": True, "review_approved": True,
        "expires_after_hours": RENDER_TTL_HOURS,
    }


@app.get("/v1/renders/{render_id}/download", dependencies=[Depends(require_service_key)])
def download_render(render_id: str, x_vyro_demo_id: str = Header(default="")) -> FileResponse:
    cleanup_expired()
    if not re.fullmatch(r"[a-f0-9]{32}", render_id):
        raise HTTPException(status_code=400, detail="Render ID tidak valid")
    namespace = demo_namespace(x_vyro_demo_id)
    root = RENDERS_DIR.resolve()
    job_dir = (root / render_id).resolve()
    path = (job_dir / "master.mp4").resolve()
    access_path = job_dir / "access.json"
    if root not in job_dir.parents or not access_path.is_file() or not path.is_file():
        raise HTTPException(status_code=404, detail="Render belum tersedia atau telah kedaluwarsa")
    try:
        access = json.loads(access_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=404, detail="Metadata render tidak ditemukan") from exc
    if access.get("demo_namespace") != namespace:
        raise HTTPException(status_code=403, detail="Render bukan milik demo ini")
    return FileResponse(path, media_type="video/mp4", filename=f"vyro-{render_id}.mp4")
