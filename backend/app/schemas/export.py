import re

from pydantic import BaseModel, Field, field_validator

from app.schemas.copy import CaptionItem, ProviderInfo, PromoItem, Style, Tone
from app.schemas.graphics import GraphicDesign, GraphicSize
from app.schemas.images import ProcessRequest


class ExportDetails(BaseModel):
    product_name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="", max_length=40)
    description: str = Field(default="", max_length=600)
    target_audience: str = Field(default="", max_length=120)
    tone: Tone = "friendly"
    brand_name: str = Field(default="", max_length=60)
    offer: str = Field(default="", max_length=80)
    style: Style = "minimal"

    @field_validator(
        "product_name", "category", "description", "target_audience", "brand_name", "offer",
        mode="before",
    )
    @classmethod
    def _tidy(cls, value: object) -> object:
        if isinstance(value, str):
            return re.sub(r"\s+", " ", value).strip()
        return value


class ExportCopy(BaseModel):
    """The text exactly as the user left it after editing (hashtags are one string)."""

    provider: ProviderInfo
    captions: list[CaptionItem] = Field(default_factory=list, max_length=20)
    hashtags: str = Field(default="", max_length=2000)
    short_descriptions: list[str] = Field(default_factory=list, max_length=10)
    promos: list[PromoItem] = Field(default_factory=list, max_length=10)
    ctas: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("short_descriptions", "ctas")
    @classmethod
    def _limit_each(cls, items: list[str]) -> list[str]:
        if any(len(i) > 2200 for i in items):
            raise ValueError("A text item is too long.")
        return items

    @field_validator("captions", "promos")
    @classmethod
    def _limit_objects(cls, items: list) -> list:
        if any(len(i.text) > 2200 for i in items):
            raise ValueError("A text item is too long.")
        return items


class ExportRequest(BaseModel):
    image_id: str = Field(min_length=1, max_length=64)
    details: ExportDetails
    copy_: ExportCopy = Field(alias="copy")
    edit: ProcessRequest = Field(default_factory=ProcessRequest)
    graphic: GraphicDesign = Field(default_factory=GraphicDesign)
    sizes: list[GraphicSize] = Field(default_factory=lambda: ["square", "portrait", "story"], min_length=1, max_length=3)
    include_json: bool = True

    model_config = {"populate_by_name": True}

    @field_validator("sizes")
    @classmethod
    def _unique(cls, sizes: list[str]) -> list[str]:
        return list(dict.fromkeys(sizes))
