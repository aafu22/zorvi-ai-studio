import logging
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.photo_assistant import PhotoAnalysis
from app.services.marketing.gemini_client import AiProviderError, GeminiClient

router = APIRouter(prefix="/photo-assistant", tags=["AI Product Photo Assistant"])
logger = logging.getLogger("zorvi.photo_assistant")
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
SYSTEM_PROMPT = """You are Zorvi AI Studio's product photography assistant. Analyse the supplied image for a small-business product listing. Describe only visible evidence; do not invent a brand, material, ingredients, price, performance, certifications, or other facts that cannot be verified from pixels. If the object is ambiguous, say so. Give practical, achievable background, composition, lighting, framing and colour suggestions that help the product stand out. Recommendations should not imply that suggested scenes are present in the original photo. Return concise, valid structured output."""


@router.post("/analyze", response_model=PhotoAnalysis)
async def analyze_photo(file: UploadFile = File(...)) -> PhotoAnalysis:
    settings = get_settings()
    if not settings.gemini_api_key.strip():
        raise HTTPException(status_code=503, detail="AI Photo Assistant needs a Gemini API key. Add GEMINI_API_KEY to backend/.env and restart the backend.")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Please upload a JPG, PNG, or WebP product photo.")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    raw = await file.read(max_bytes + 1)
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(raw) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Image is too large. Please keep it under {settings.max_upload_mb} MB.")
    try:
        with Image.open(BytesIO(raw)) as img:
            img.verify()
        with Image.open(BytesIO(raw)) as img:
            image_format = (img.format or "").upper()
            if image_format not in {"JPEG", "PNG", "WEBP"}:
                raise HTTPException(status_code=415, detail="Please upload a JPG, PNG, or WebP product photo.")
            img = img.convert("RGB")
            img.thumbnail((1600, 1600))
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=88)
            image_bytes = buffer.getvalue()
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(status_code=400, detail="That file could not be read as an image. Try another JPG, PNG, or WebP photo.") from None
    finally:
        await file.close()
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise HTTPException(status_code=503, detail="The Google AI package is missing. In the backend folder run: pip install -r requirements.txt") from None
    try:
        client = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=settings.gemini_timeout_seconds * 1000))
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                "Analyse this product photo and return the requested structured product photography recommendations.",
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.35,
                response_mime_type="application/json",
                response_schema=PhotoAnalysis,
            ),
        )
        if not getattr(response, "parsed", None):
            text = getattr(response, "text", None)
            if not text:
                raise HTTPException(status_code=502, detail="The AI returned an empty result. Please try again.")
            return PhotoAnalysis.model_validate_json(text)
        return PhotoAnalysis.model_validate(response.parsed)
    except HTTPException:
        raise
    except Exception as exc:  # never log uploaded image content or API credentials
        code = getattr(exc, "code", None)
        message = str(getattr(exc, "message", "") or exc).lower()
        logger.warning("Photo analysis failed: %s (code=%s)", type(exc).__name__, code)
        if code == 429 or "quota" in message or "resource_exhausted" in message:
            raise HTTPException(status_code=429, detail="The Gemini free-tier limit may have been reached. Wait a while or check your Google AI usage limits.") from None
        if code in (401, 403) or "api key" in message or "api_key" in message:
            raise HTTPException(status_code=502, detail="Gemini rejected the API key. Check GEMINI_API_KEY in backend/.env.") from None
        if code == 404:
            raise HTTPException(status_code=502, detail="The configured Gemini model was not found. Check GEMINI_MODEL in backend/.env.") from None
        if code in (408, 504) or "timeout" in message:
            raise HTTPException(status_code=504, detail="Image analysis took too long. Try again with a smaller photo.") from None
        if isinstance(exc, ValidationError):
            raise HTTPException(status_code=502, detail="The AI returned a result in an unexpected format. Please try again.") from None
        raise HTTPException(status_code=502, detail="The AI photo analysis failed. Check the backend terminal and try again.") from None
