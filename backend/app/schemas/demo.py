from pydantic import BaseModel

from app.schemas.copy import Style, Tone
from app.schemas.images import UploadResponse


class DemoDetails(BaseModel):
    product_name: str
    category: str
    description: str
    target_audience: str
    tone: Tone
    brand_name: str
    offer: str


class DemoResponse(BaseModel):
    image: UploadResponse
    details: DemoDetails
    style: Style
