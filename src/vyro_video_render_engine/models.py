from pydantic import BaseModel, ConfigDict, Field

class Scene(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scene_number: int = Field(ge=1)
    duration_seconds: float = Field(gt=0, le=45)
    visual_direction: str = Field(min_length=3)
    on_screen_text: str = Field(min_length=1, max_length=200)
    voiceover: str = ""
    asset_hint: str | None = None

class ContentPackage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content_id: str
    title: str
    duration_seconds: int = Field(ge=8, le=90)
    selected_hook: str
    narration: str
    scenes: list[Scene] = Field(min_length=1, max_length=12)
    caption: str
    human_review_required: bool = True
