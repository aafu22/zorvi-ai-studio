import re

from pydantic import BaseModel, Field, field_validator

from app.schemas.copy import Tone
from app.schemas.graphics import FontId, GraphicColors


class BrandKitIn(BaseModel):
    brand_name: str = Field(default="", max_length=40)
    colors: GraphicColors = Field(default_factory=GraphicColors)
    font: FontId = "sans"
    tone: Tone = "friendly"

    @field_validator("brand_name", mode="before")
    @classmethod
    def _tidy(cls, value: object) -> object:
        if isinstance(value, str):
            return re.sub(r"\s+", " ", value).strip()
        return value


class BrandKitOut(BrandKitIn):
    configured: bool = False  # False until the user saves the kit at least once
    has_logo: bool = False
    logo_url: str | None = None
