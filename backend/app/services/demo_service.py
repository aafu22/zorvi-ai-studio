"""Demo mode: a ready-made sample product so people can try the app without uploading anything.

The sample photo (sample_assets/sample-product.jpg) was drawn with Pillow by
sample_assets/make_sample_product.py, so it has no third-party licence. It is an illustration,
not a photograph.
"""

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.demo import DemoDetails, DemoResponse
from app.schemas.images import UploadResponse
from app.services import image_service
from app.services.storage_service import get_storage

SAMPLE_FILE = "sample-product.jpg"

SAMPLE_DETAILS = DemoDetails(
    product_name="Amber Glow Soy Candle",
    category="Candles & fragrance",
    description="Soy wax candle in an amber glass jar. 200 g. Comes with a cotton wick and a kraft gift box.",
    target_audience="people who love cosy evenings at home",
    tone="friendly",
    brand_name="Hearth & Honey",
    offer="15% off this week",
)
SAMPLE_STYLE = "aesthetic"


def start_demo() -> DemoResponse:
    """Copy the sample photo in as a fresh temporary upload and return the sample details."""
    path = get_settings().sample_assets_path / SAMPLE_FILE
    if not path.is_file():
        raise AppError(404, "The sample product photo is missing from the sample_assets folder.")
    data = path.read_bytes()
    info = image_service.inspect_image(data)
    image_id = get_storage().save_original(data, "jpg")
    return DemoResponse(
        image=UploadResponse(
            id=image_id, width=info.width, height=info.height, format=info.format,
            size_bytes=len(data), original_url=f"/api/images/{image_id}/original",
        ),
        details=SAMPLE_DETAILS,
        style=SAMPLE_STYLE,
    )
