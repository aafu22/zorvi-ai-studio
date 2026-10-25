import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.images import UploadResponse

MAX_STATE_CHARS = 200_000


class SaveCampaignRequest(BaseModel):
    image_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    product_name: str = Field(default="", max_length=80)
    # The editor's settings, copy and graphic design. Stored as-is and handed back on open.
    state: dict[str, Any]

    @field_validator("name", "product_name", mode="before")
    @classmethod
    def _tidy(cls, value: object) -> object:
        if isinstance(value, str):
            return re.sub(r"\s+", " ", value).strip()
        return value

    @field_validator("state")
    @classmethod
    def _limit_state(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value)) > MAX_STATE_CHARS:
            raise ValueError("Saved project data is too large.")
        return value


class CampaignSummary(BaseModel):
    id: int
    name: str
    product_name: str
    created_at: str
    thumbnail_url: str
    photo_url: str


class OpenCampaignResponse(BaseModel):
    image: UploadResponse  # the photo, restored under a fresh upload id
    state: dict[str, Any]
