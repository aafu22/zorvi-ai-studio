import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Tone = Literal["friendly", "professional", "luxury", "playful", "festive"]
Style = Literal["minimal", "luxury", "aesthetic", "festive", "vibrant"]
ProviderId = Literal["template"]  # add "llm" here when an LLM provider is implemented


class CopyRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=80)
    category: str = Field(default="", max_length=40)
    description: str = Field(default="", max_length=600)
    target_audience: str = Field(default="", max_length=120)
    tone: Tone = "friendly"
    style: Style = "minimal"
    brand_name: str = Field(default="", max_length=60)
    offer: str = Field(default="", max_length=80)
    provider: ProviderId = "template"
    # Same seed + same input = same output (used in tests). Omit for a fresh variation each time.
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1)

    @field_validator(
        "product_name", "category", "description", "target_audience", "brand_name", "offer",
        mode="before",
    )
    @classmethod
    def _tidy(cls, value: object) -> object:
        """Trim and collapse whitespace so templates never produce double spaces."""
        if isinstance(value, str):
            return re.sub(r"\s+", " ", value).strip()
        return value


class ProviderInfo(BaseModel):
    id: str
    label: str
    is_ai: bool  # the UI uses this so template output is never presented as AI-written


class CaptionItem(BaseModel):
    tone: Tone
    text: str


class PromoItem(BaseModel):
    kind: Literal["headline", "ad", "story"]
    text: str


class CopyResponse(BaseModel):
    provider: ProviderInfo
    captions: list[CaptionItem]
    hashtags: list[str]
    short_descriptions: list[str]
    promos: list[PromoItem]
    ctas: list[str]
