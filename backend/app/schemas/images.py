from typing import Literal

from pydantic import BaseModel, Field

Preset = Literal["original", "square", "portrait", "story"]
Fit = Literal["cover", "contain"]
OutputFormat = Literal["png", "jpeg"]

HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class UploadResponse(BaseModel):
    id: str
    width: int
    height: int
    format: str
    size_bytes: int
    original_url: str


class ProcessRequest(BaseModel):
    """Edit settings. The original upload is never modified; every call renders a new image."""

    preset: Preset = "square"
    # cover   = fill the frame, cropping the overflow (zoom / focus apply)
    # contain = fit the whole photo inside the frame and fill the rest with `background`
    fit: Fit = "contain"
    background: str = Field(default="#ffffff", pattern=HEX_COLOR)
    zoom: float = Field(default=1.0, ge=1.0, le=4.0)
    focus_x: float = Field(default=0.5, ge=0.0, le=1.0)
    focus_y: float = Field(default=0.5, ge=0.0, le=1.0)
    brightness: float = Field(default=1.0, ge=0.5, le=1.5)
    contrast: float = Field(default=1.0, ge=0.5, le=1.5)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)
    output_format: OutputFormat = "png"
