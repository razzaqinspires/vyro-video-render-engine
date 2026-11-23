from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Scene(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scene_number: int = Field(ge=1, le=20)
    duration_seconds: float = Field(gt=0, le=45)
    visual_direction: str = Field(min_length=3, max_length=700)
    visual_prompt: str = Field(default="", max_length=4000)
    visual_style: str = Field(default="", max_length=500)
    on_screen_text: str = Field(min_length=1, max_length=200)
    voiceover: str = Field(default="", max_length=900)
    asset_hint: str | None = Field(default=None, max_length=240)
    asset_rationale: str | None = Field(default=None, max_length=500)


class ContentPackage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schema_version: str = "1.3"
    content_id: str = Field(min_length=4, max_length=80)
    title: str
    duration_seconds: int = Field(ge=8, le=90)
    selected_hook: str
    narration: str
    scenes: list[Scene] = Field(min_length=2, max_length=12)
    caption: str = Field(max_length=2200)
    human_review_required: bool = True
    review_approved: bool = False

    @classmethod
    def validate_content_id(cls, value: str) -> str:
        import re
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", value) or ".." in value:
            raise ValueError("content_id tidak valid")
        return value
