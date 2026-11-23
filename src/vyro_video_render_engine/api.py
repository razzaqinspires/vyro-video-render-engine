from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from .models import ContentPackage
from .renderer import render
from .upload_validation import validate_asset_signature

APP_VERSION = "1.2.0"
app = FastAPI(title="VYRO Video Render Engine API", version=APP_VERSION)
ASSETS_DIR = Path(os.getenv("VYRO_RENDER_ASSETS_DIR", "./api_assets")).expanduser().resolve()
RENDERS_DIR = Path(os.getenv("VYRO_RENDER_OUTPUT_DIR", "./api_renders")).expanduser().resolve()
MAX_ASSET_BYTES = max(1024 * 1024, min(int(os.getenv("VYRO_RENDER_MAX_ASSET_BYTES", str(20 * 1024 * 1024))), 50 * 1024 * 1024))
ASSET_TTL_HOURS = max(1, min(int(os.getenv("VYRO_RENDER_ASSET_TTL_HOURS", "48")), 720))
RENDER_TTL_HOURS = max(1, min(int(os.getenv("VYRO_RENDER_OUTPUT_TTL_HOURS", "72")), 720))
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".m4a"}


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


def cleanup_expired() -> None:
    now = datetime.now(timezone.utc)
    if ASSETS_DIR.exists():
        for meta in ASSETS_DIR.glob("*/*.meta.json"):
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                created = datetime.fromisoformat(data["created_at"])
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if now - created > timedelta(hours=ASSET_TTL_HOURS):
                    asset = meta.with_name(meta.name.removesuffix(".meta.json"))
                    asset.unlink(missing_ok=True)
                    meta.unlink(missing_ok=True)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue
    if RENDERS_DIR.exists():
        for folder in RENDERS_DIR.iterdir():
            if not folder.is_dir():
                continue
            try:
                manifest = folder / "access.json"
                if not manifest.is_file():
                    continue
                data = json.loads(manifest.read_text(encoding="utf-8"))
                created = datetime.fromisoformat(data["created_at"])
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if now - created > timedelta(hours=RENDER_TTL_HOURS):
                    shutil.rmtree(folder, ignore_errors=True)
            except (OSError, ValueError, KeyError, json.JSONDecodeError):
                continue


class AssetUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=180)
    data_base64: str = Field(min_length=16, max_length=30_000_000)


class RenderRequest(BaseModel):
    content_package: dict[str, Any]
    voiceover_asset: str | None = Field(default=None, max_length=120)


@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "vyro-video-render-engine", "status": "ok", "version": APP_VERSION}


@app.post("/v1/assets", dependencies=[Depends(require_service_key)])
def upload_asset(payload: AssetUpload, x_vyro_demo_id: str = Header(default="")) -> dict[str, Any]:
    cleanup_expired()
    namespace = demo_namespace(x_vyro_demo_id)
    suffix = Path(payload.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Format aset tidak didukung")
    try:
        data = base64.b64decode(payload.data_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Base64 tidak valid") from exc
    if not data or len(data) > MAX_ASSET_BYTES:
        raise HTTPException(status_code=413, detail="Ukuran aset melewati batas layanan")
    folder = ASSETS_DIR / namespace
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{suffix}"
    target = folder / filename
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_bytes(data)
    temp.replace(target)
    metadata = {
        "asset_ref": f"{namespace}/{filename}", "demo_namespace": namespace,
        "original_filename": Path(payload.filename).name, "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "created_at": datetime.now(timezone.utc).isoformat(),
    }
    target.with_name(target.name + ".meta.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"asset_ref": metadata["asset_ref"], "bytes": len(data), "media_type": suffix.lstrip("."), "expires_after_hours": ASSET_TTL_HOURS}


@app.post("/v1/render", dependencies=[Depends(require_service_key)])
def render_package(payload: RenderRequest, x_vyro_demo_id: str = Header(default="")) -> dict[str, Any]:
    cleanup_expired()
    namespace = demo_namespace(x_vyro_demo_id)
    if payload.content_package.get("human_review_required", True) and payload.content_package.get("review_approved") is not True:
        raise HTTPException(status_code=409, detail="ContentPackage harus disetujui manusia sebelum render final")
    try:
        package = ContentPackage.model_validate(payload.content_package)
        ContentPackage.validate_content_id(package.content_id)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for scene in package.scenes:
        if scene.asset_hint:
            ref = scene.asset_hint
            if not re.fullmatch(r"[a-f0-9]{24}/[a-f0-9]{32}\.(png|jpg|jpeg|webp)", ref):
                raise HTTPException(status_code=422, detail="Scene asset reference tidak valid")
            if not ref.startswith(namespace + "/"):
                raise HTTPException(status_code=403, detail="Scene asset bukan milik demo ini")
            candidate = (ASSETS_DIR / ref).resolve()
            if ASSETS_DIR not in candidate.parents or not candidate.is_file():
                raise HTTPException(status_code=404, detail="Scene asset tidak ditemukan")
            meta_path = candidate.with_name(candidate.name + ".meta.json")
            if not meta_path.is_file() or json.loads(meta_path.read_text(encoding="utf-8")).get("demo_namespace") != namespace:
                raise HTTPException(status_code=403, detail="Hak akses scene asset tidak valid")

    voiceover = None
    if payload.voiceover_asset:
        ref = payload.voiceover_asset
        if not re.fullmatch(r"[a-f0-9]{24}/[a-f0-9]{32}\.(wav|mp3|m4a)", ref) or not ref.startswith(namespace + "/"):
            raise HTTPException(status_code=403, detail="Voiceover asset reference tidak valid")
        voiceover = (ASSETS_DIR / ref).resolve()
        if ASSETS_DIR not in voiceover.parents or not voiceover.is_file():
            raise HTTPException(status_code=404, detail="Voiceover asset tidak ditemukan")
        meta_path = voiceover.with_name(voiceover.name + ".meta.json")
        if not meta_path.is_file() or json.loads(meta_path.read_text(encoding="utf-8")).get("demo_namespace") != namespace:
            raise HTTPException(status_code=403, detail="Hak akses voiceover asset tidak valid")

    render_id = uuid.uuid4().hex
    job_dir = RENDERS_DIR / render_id
    output = job_dir / "master.mp4"
    workdir = job_dir / "work"
    job_dir.mkdir(parents=True, exist_ok=False)
    try:
        with TemporaryDirectory(prefix="vyro-package-") as temp:
            source = Path(temp) / "content-package.json"
            source.write_text(json.dumps(package.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
            manifest = render(source, output, workdir, ASSETS_DIR, voiceover)
        access = {"render_id": render_id, "demo_namespace": namespace, "created_at": datetime.now(timezone.utc).isoformat()}
        (job_dir / "access.json").write_text(json.dumps(access, indent=2), encoding="utf-8")
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "render_id": render_id, "status": "rendered", "manifest": manifest,
        "download_url": f"/v1/renders/{render_id}/download", "human_review_required": True,
        "expires_after_hours": RENDER_TTL_HOURS,
    }


@app.get("/v1/renders/{render_id}/download", dependencies=[Depends(require_service_key)])
def download_render(render_id: str, x_vyro_demo_id: str = Header(default="")):
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
    access = json.loads(access_path.read_text(encoding="utf-8"))
    if access.get("demo_namespace") != namespace:
        raise HTTPException(status_code=403, detail="Render bukan milik demo ini")
    return FileResponse(path, media_type="video/mp4", filename=f"vyro-{render_id}.mp4")
