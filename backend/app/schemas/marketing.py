import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Category = Literal["fashion", "beauty", "food", "electronics", "handmade", "other"]
Goal = Literal["launch", "sales", "awareness", "seasonal", "engagement"]
Platform = Literal["instagram", "facebook", "whatsapp", "general"]
MarketingTone = Literal["friendly", "professional", "playful", "elegant", "persuasive", "minimal"]
Section = Literal["all", "captions", "hashtags", "headlines", "description", "ctas", "promo", "ideas"]


class MarketingRequest(BaseModel):
    product_name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=600)
    category: Category = "other"
    price: str = Field(default="", max_length=40)
    offer: str = Field(default="", max_length=80)
    target_audience: str = Field(default="", max_length=120)
    brand_name: str = Field(default="", max_length=60)
    goal: Goal = "sales"
    platform: Platform = "instagram"
    tone: MarketingTone = "friendly"
    # "all" builds the whole kit; any other value regenerates just that one section.
    section: Section = "all"

    @field_validator(
        "product_name", "description", "price", "offer", "target_audience", "brand_name", mode="before"
    )
    @classmethod
    def _tidy(cls, value: object) -> object:
        """Trim and collapse whitespace."""
        if isinstance(value, str):
            return re.sub(r"\s+", " ", value).strip()
        return value


class MarketingSource(BaseModel):
    id: Literal["gemini", "template"]
    label: str
    is_ai: bool  # the UI uses this so template output is never presented as AI-written
    model: str | None = None


class MarketingContent(BaseModel):
    """Every field is optional because a single-section regenerate returns only that section."""

    captions: list[str] | None = None
    hashtags: list[str] | None = None
    headlines: list[str] | None = None
    description: str | None = None
    ctas: list[str] | None = None
    promo: str | None = None
    ideas: list[str] | None = None


class MarketingResponse(BaseModel):
    source: MarketingSource
    section: Section
    content: MarketingContent
    # Things worth double-checking, e.g. a number that was not in your brief.
    warnings: list[str] = []
