import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.images import HEX_COLOR, Fit, OutputFormat

GraphicSize = Literal["square", "portrait", "story"]
TemplateId = Literal["classic", "overlay", "frame", "offer"]
FontId = Literal["sans", "serif", "display"]


class GraphicColors(BaseModel):
    background: str = Field(default="#ffffff", pattern=HEX_COLOR)
    text: str = Field(default="#0f172a", pattern=HEX_COLOR)
    accent: str = Field(default="#4f46e5", pattern=HEX_COLOR)


class PhotoSettings(BaseModel):
    """How the product photo sits in the template's photo area (same meaning as in the editor)."""

    fit: Fit = "cover"
    background: str = Field(default="#ffffff", pattern=HEX_COLOR)
    zoom: float = Field(default=1.0, ge=1.0, le=4.0)
    focus_x: float = Field(default=0.5, ge=0.0, le=1.0)
    focus_y: float = Field(default=0.5, ge=0.0, le=1.0)
    brightness: float = Field(default=1.0, ge=0.5, le=1.5)
    contrast: float = Field(default=1.0, ge=0.5, le=1.5)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)


class GraphicDesign(BaseModel):
    """Everything about how a graphic looks, without saying which photo it uses."""

    template: TemplateId = "classic"
    size: GraphicSize = "square"
    font: FontId = "sans"
    headline: str = Field(default="", max_length=60)
    subheadline: str = Field(default="", max_length=120)
    cta: str = Field(default="", max_length=30)
    badge: str = Field(default="", max_length=14)  # only drawn by the "offer" template
    brand_name: str = Field(default="", max_length=40)
    colors: GraphicColors = Field(default_factory=GraphicColors)
    photo: PhotoSettings = Field(default_factory=PhotoSettings)
    show_logo: bool = False  # draws the Brand Kit logo (ignored if no logo has been uploaded)
    output_format: OutputFormat = "png"

    @field_validator("headline", "subheadline", "cta", "badge", "brand_name", mode="before")
    @classmethod
    def _tidy(cls, value: object) -> object:
        if isinstance(value, str):
            return re.sub(r"\s+", " ", value).strip()
        return value


class GraphicRequest(GraphicDesign):
    image_id: str = Field(min_length=1, max_length=64)


class TemplateInfo(BaseModel):
    id: TemplateId
    label: str
    description: str
    uses_badge: bool = False


class SizeInfo(BaseModel):
    id: GraphicSize
    label: str
    width: int
    height: int
    note: str = ""


class FontInfo(BaseModel):
    id: FontId
    label: str


class GraphicOptions(BaseModel):
    templates: list[TemplateInfo]
    sizes: list[SizeInfo]
    fonts: list[FontInfo]
