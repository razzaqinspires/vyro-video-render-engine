from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Clip(StrictModel):
    """One timeline item. `asset_ref` is a demo-scoped reference returned by /v1/assets."""

    clip_id: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]+$")
    track_id: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    kind: Literal["video", "image", "audio", "text"]
    start_seconds: float = Field(ge=0, le=180)
    duration_seconds: float = Field(gt=0, le=180)
    source_in_seconds: float = Field(default=0, ge=0, le=36000)
    asset_ref: str | None = Field(default=None, max_length=120)
    text: str | None = Field(default=None, max_length=500)
    font_size: int = Field(default=68, ge=12, le=180)
    font_color: str = Field(default="#FAFCFA", pattern=r"^#[0-9A-Fa-f]{6}$")
    background_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    x: float = Field(default=0.5, ge=0, le=1)
    y: float = Field(default=0.5, ge=0, le=1)
    fit: Literal["cover", "contain"] = "cover"
    volume: float = Field(default=1.0, ge=0, le=2)
    fade_in_seconds: float = Field(default=0, ge=0, le=15)
    fade_out_seconds: float = Field(default=0, ge=0, le=15)
    enabled: bool = True

    @model_validator(mode="after")
    def validate_kind_fields(self) -> "Clip":
        if self.kind in {"video", "image", "audio"} and not self.asset_ref:
            raise ValueError(f"{self.kind} clip requires asset_ref")
        if self.kind == "text" and not self.text:
            raise ValueError("text clip requires text")
        if self.fade_in_seconds + self.fade_out_seconds > self.duration_seconds:
            raise ValueError("combined fade duration cannot exceed clip duration")
        return self


class Track(StrictModel):
    track_id: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=64)
    kind: Literal["video", "audio", "overlay"]
    order: int = Field(ge=0, le=32)
    muted: bool = False
    locked: bool = False


class Timeline(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    title: str = Field(default="Untitled VYRO Project", min_length=1, max_length=160)
    width: int = Field(default=1080, ge=256, le=3840)
    height: int = Field(default=1920, ge=256, le=3840)
    fps: int = Field(default=30, ge=24, le=60)
    duration_seconds: float = Field(ge=1, le=180)
    background_color: str = Field(default="#050708", pattern=r"^#[0-9A-Fa-f]{6}$")
    tracks: list[Track] = Field(min_length=1, max_length=16)
    clips: list[Clip] = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_timeline(self) -> "Timeline":
        track_ids = [track.track_id for track in self.tracks]
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("track_id values must be unique")
        clip_ids = [clip.clip_id for clip in self.clips]
        if len(clip_ids) != len(set(clip_ids)):
            raise ValueError("clip_id values must be unique")
        track_map = {track.track_id: track for track in self.tracks}
        for clip in self.clips:
            if clip.track_id not in track_map:
                raise ValueError(f"unknown track_id: {clip.track_id}")
            track = track_map[clip.track_id]
            if track.kind == "audio" and clip.kind not in {"audio"}:
                raise ValueError("audio tracks may only contain audio clips")
            if track.kind == "overlay" and clip.kind not in {"text", "image"}:
                raise ValueError("overlay tracks may only contain text or image clips")
            if track.kind == "video" and clip.kind not in {"video", "image"}:
                raise ValueError("video tracks may only contain video or image clips")
            if clip.start_seconds + clip.duration_seconds > self.duration_seconds + 0.001:
                raise ValueError(f"clip exceeds project duration: {clip.clip_id}")
            if clip.fade_in_seconds > clip.duration_seconds or clip.fade_out_seconds > clip.duration_seconds:
                raise ValueError("fade duration exceeds clip duration")
        if not any(c.enabled and c.kind in {"video", "image", "text"} for c in self.clips):
            raise ValueError("timeline needs at least one enabled visual clip")
        return self


class Scene(StrictModel):
    scene_number: int = Field(ge=1, le=20)
    duration_seconds: float = Field(gt=0, le=45)
    visual_direction: str = Field(min_length=3, max_length=700)
    visual_prompt: str = Field(default="", max_length=4000)
    visual_style: str = Field(default="", max_length=500)
    on_screen_text: str = Field(min_length=1, max_length=200)
    voiceover: str = Field(default="", max_length=900)
    asset_hint: str | None = Field(default=None, max_length=240)
    asset_rationale: str | None = Field(default=None, max_length=500)


class ContentPackage(StrictModel):
    schema_version: str = "1.3"
    content_id: str = Field(min_length=4, max_length=80)
    title: str = Field(min_length=1, max_length=160)
    duration_seconds: int = Field(ge=8, le=90)
    selected_hook: str = Field(min_length=1, max_length=400)
    narration: str = Field(default="", max_length=12000)
    scenes: list[Scene] = Field(min_length=2, max_length=12)
    caption: str = Field(default="", max_length=2200)
    human_review_required: bool = True
    review_approved: bool = False

    @field_validator("content_id")
    @classmethod
    def validate_content_id(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", value) or ".." in value:
            raise ValueError("content_id tidak valid")
        return value

    @model_validator(mode="after")
    def validate_scene_timing(self) -> "ContentPackage":
        if sum(scene.duration_seconds for scene in self.scenes) > self.duration_seconds + 0.001:
            raise ValueError("total scene durations exceed package duration")
        return self
