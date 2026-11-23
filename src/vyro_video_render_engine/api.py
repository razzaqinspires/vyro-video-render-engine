from __future__ import annotations

import base64
import binascii
import hmac
import json
import os
import re
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

from .models import ContentPackage
from .renderer import render

app = FastAPI(title="VYRO Video Render Engine API", version="1.1.0")
ASSETS_DIR = Path(os.getenv("VYRO_RENDER_ASSETS_DIR", "./api_assets")).expanduser().resolve()
RENDERS_DIR = Path(os.getenv("VYRO_RENDER_OUTPUT_DIR", "./api_renders")).expanduser().resolve()
MAX_ASSET_BYTES = int(os.getenv("VYRO_RENDER_MAX_ASSET_BYTES", str(20 * 1024 * 1024)))
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".m4a"}

def require_service_key(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("VYRO_SERVICE_API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Service API key belum dikonfigurasi")
    supplied = authorization.removeprefix("Bearer ") if authorization else ""
    if not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")

class AssetUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=180)
    data_base64: str = Field(min_length=16, max_length=30_000_000)

class RenderRequest(BaseModel):
    content_package: dict[str, Any]
    voiceover_asset: str | None = Field(default=None, max_length=100)

@app.get("/health")
def health() -> dict[str, str]:
    return {"service": "vyro-video-render-engine", "status": "ok", "version": "1.1.0"}

@app.post("/v1/assets", dependencies=[Depends(require_service_key)])
def upload_asset(payload: AssetUpload) -> dict[str, Any]:
    suffix = Path(payload.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Format aset tidak didukung")
    try:
        data = base64.b64decode(payload.data_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Base64 tidak valid") from exc
    if not data or len(data) > MAX_ASSET_BYTES:
        raise HTTPException(status_code=413, detail="Ukuran aset melewati batas layanan")
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    asset_ref = f"{uuid.uuid4().hex}{suffix}"
    (ASSETS_DIR / asset_ref).write_bytes(data)
    return {"asset_ref": asset_ref, "bytes": len(data), "media_type": suffix.lstrip(".")}

@app.post("/v1/render", dependencies=[Depends(require_service_key)])
def render_package(payload: RenderRequest) -> dict[str, Any]:
    if payload.content_package.get("human_review_required", True) and payload.content_package.get("review_approved") is not True:
        raise HTTPException(status_code=409, detail="ContentPackage harus disetujui manusia sebelum render final")
    try:
        package = ContentPackage.model_validate(payload.content_package)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors(include_url=False)) from exc
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for scene in package.scenes:
        if scene.asset_hint:
            if Path(scene.asset_hint).name != scene.asset_hint or not (ASSETS_DIR / scene.asset_hint).is_file():
                raise HTTPException(status_code=422, detail=f"Scene asset tidak ditemukan/diizinkan: {scene.asset_hint}")
    voiceover = None
    if payload.voiceover_asset:
        if Path(payload.voiceover_asset).name != payload.voiceover_asset:
            raise HTTPException(status_code=400, detail="Voiceover asset ref tidak valid")
        voiceover = (ASSETS_DIR / payload.voiceover_asset).resolve()
        if ASSETS_DIR not in voiceover.parents or not voiceover.is_file():
            raise HTTPException(status_code=404, detail="Voiceover asset tidak ditemukan")
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
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"render_id": render_id, "status": "rendered", "manifest": manifest, "download_url": f"/v1/renders/{render_id}/download", "human_review_required": True}

@app.get("/v1/renders/{render_id}/download", dependencies=[Depends(require_service_key)])
def download_render(render_id: str):
    if not re.fullmatch(r"[a-f0-9]{32}", render_id):
        raise HTTPException(status_code=400, detail="Render ID tidak valid")
    root = RENDERS_DIR.resolve()
    path = (root / render_id / "master.mp4").resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Render belum tersedia")
    return FileResponse(path, media_type="video/mp4", filename=f"vyro-{render_id}.mp4")
