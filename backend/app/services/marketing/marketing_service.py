"""AI Marketing Brain: build the prompt, call Gemini, check and tidy the answer.

If Gemini is unavailable this raises AppError with a plain-English message. It never quietly swaps in
template text: the template version is a separate, clearly labelled call (template_marketing).
"""

import json
import logging
import re
from typing import Protocol

from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.copy import CopyRequest
from app.schemas.marketing import (
    MarketingContent,
    MarketingRequest,
    MarketingResponse,
    MarketingSource,
)
from app.services.copywriting.rule_based import RuleBasedProvider
from app.services.marketing.gemini_client import AiProviderError, GeminiClient
from app.services.marketing.prompt import SECTION_NAMES, SECTION_SCHEMAS, SYSTEM_INSTRUCTION, build_prompt

logger = logging.getLogger(__name__)

# How many items each list section must contain.
EXACT_COUNTS = {"captions": 3, "headlines": 5, "ctas": 3, "ideas": 3}
HASHTAG_MIN, HASHTAG_MAX = 5, 15

TEMPLATE_SOURCE = MarketingSource(id="template", label="Template-based (not AI-generated)", is_ai=False)


class JsonModelClient(Protocol):
    """What this service needs from an AI client. GeminiClient implements it; tests use a fake."""

    @property
    def model(self) -> str: ...

    def generate_json(self, system: str, prompt: str, schema: type[BaseModel]) -> str: ...


class BadModelOutput(Exception):
    pass


# ----------------------------------------------------------------- client + errors


def default_client() -> JsonModelClient:
    settings = get_settings()
    if not settings.llm_configured:
        raise AppError(
            503,
            "AI Marketing Brain needs a Gemini API key. Add GEMINI_API_KEY to backend/.env and restart the "
            "backend. You can still use the template-based version meanwhile.",
        )
    try:
        return GeminiClient(settings.gemini_api_key.strip(), settings.gemini_model, settings.gemini_timeout_seconds)
    except AiProviderError as exc:
        raise _to_app_error(exc) from None


def _to_app_error(exc: AiProviderError) -> AppError:
    table = {
        "auth": (502, "Gemini rejected the API key. Check GEMINI_API_KEY in backend/.env."),
        "rate_limit": (429, "Gemini's rate limit or quota was reached. Wait a minute and try again."),
        "timeout": (504, "Gemini took too long to answer. Try again."),
        "not_installed": (503, exc.message),
        "bad_request": (502, exc.message),
        "unavailable": (502, "Gemini is temporarily unavailable. Try again shortly."),
    }
    status, detail = table[exc.kind]
    return AppError(status, detail)


# ----------------------------------------------------------------- parsing + checks


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_list(items: list[str]) -> list[str]:
    return [t for t in (_clean(i) for i in items if isinstance(i, str)) if t]


def _clean_hashtags(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        body = re.sub(r"[^\w]", "", str(raw).lstrip("#"))
        if not body or body.lower() in seen:
            continue
        seen.add(body.lower())
        out.append(f"#{body}")
    return out[:HASHTAG_MAX]


def parse_content(raw: str, section: str) -> MarketingContent:
    """Turn the model's JSON text into validated, tidied content for the requested section(s)."""
    try:
        data = SECTION_SCHEMAS[section].model_validate(json.loads(raw)).model_dump()
    except (ValueError, ValidationError) as exc:
        raise BadModelOutput("The AI reply was not in the expected format.") from exc

    content: dict[str, object] = {}
    for name, value in data.items():
        if name in ("description", "promo"):
            text = _clean(value)
            if not text:
                raise BadModelOutput(f"The AI reply had an empty {name}.")
            content[name] = text
        elif name == "hashtags":
            tags = _clean_hashtags(value)
            if len(tags) < HASHTAG_MIN:
                raise BadModelOutput("The AI reply had too few hashtags.")
            content[name] = tags
        else:
            items = _clean_list(value)
            need = EXACT_COUNTS[name]
            if len(items) < need:
                raise BadModelOutput(f"The AI reply had too few {name}.")
            content[name] = items[:need]
    return MarketingContent(**content)


_NUMBER = re.compile(r"\d[\d,.]*")
# Claims a seller may not be able to back up. Flagged only when the brief did not contain the term.
_RISKY_TERMS = (
    "limited stock", "limited edition", "limited time", "only a few", "selling fast", "sold out",
    "best-selling", "bestselling", "bestseller", "best seller", "guaranteed", "certified", "award",
    "clinically", "dermatologist", "organic", "free shipping", "free delivery", "money-back",
    "reviews", "five-star", "5-star", "rated", "#1",
)


def _numbers(text: str) -> set[str]:
    return {m.group().strip(".,") for m in _NUMBER.finditer(text)}


def check_claims(req: MarketingRequest, content: MarketingContent) -> list[str]:
    """Return warnings for numbers or risky claims that appear in the output but not in the brief."""
    brief = " ".join([req.product_name, req.description, req.price, req.offer, req.target_audience, req.brand_name])
    brief_lower = brief.lower()
    known_numbers = _numbers(brief)

    texts: list[str] = []
    for name, value in content.model_dump().items():
        if name == "hashtags" or value is None:  # hashtags may legitimately contain years etc.
            continue
        texts.extend(value if isinstance(value, list) else [value])

    warnings: list[str] = []
    for number in sorted({n for t in texts for n in _numbers(t)} - known_numbers):
        if number:
            warnings.append(f'The number "{number}" appears in the generated text but not in your brief. Check it before posting.')
    joined = " ".join(texts).lower()
    for term in _RISKY_TERMS:
        if term in joined and term not in brief_lower:
            warnings.append(f'The text mentions "{term}", which was not in your brief. Remove it unless it is true.')
    return warnings


# ----------------------------------------------------------------- public API


def generate_marketing(req: MarketingRequest, client: JsonModelClient | None = None) -> MarketingResponse:
    client = client or default_client()
    schema = SECTION_SCHEMAS[req.section]

    best: tuple[MarketingContent, list[str]] | None = None
    reminder = ""
    for attempt in range(2):
        try:
            raw = client.generate_json(SYSTEM_INSTRUCTION, build_prompt(req, reminder), schema)
        except AiProviderError as exc:
            raise _to_app_error(exc) from None
        try:
            content = parse_content(raw, req.section)
        except BadModelOutput as exc:
            logger.warning("Unusable Gemini output (attempt %d): %s", attempt + 1, exc)
            reminder = "Your previous answer was unusable. Follow the requested counts and the JSON schema exactly."
            continue
        warnings = check_claims(req, content)
        if best is None or len(warnings) < len(best[1]):
            best = (content, warnings)
        if not warnings:
            break
        reminder = "Your previous answer contained numbers or claims that are not in the brief. Remove them."

    if best is None:
        raise AppError(502, "The AI returned an answer we could not use. Please try again.")
    content, warnings = best
    return MarketingResponse(
        source=MarketingSource(id="gemini", label="Generated by Google Gemini", is_ai=True, model=client.model),
        section=req.section,
        content=content,
        warnings=warnings,
    )


_TONE_TO_COPY = {
    "friendly": "friendly", "professional": "professional", "playful": "playful",
    "elegant": "luxury", "persuasive": "professional", "minimal": "professional",
}
_STYLE_FOR_TONE = {"elegant": "luxury", "playful": "vibrant"}
_CATEGORY_LABEL = {"fashion": "Fashion & clothing", "beauty": "Beauty & skincare", "food": "Food & bakery"}

_TEMPLATE_IDEAS = [
    "Post a close-up photo of the product on a plain background, then a second photo showing it in everyday use.",
    "Record a short video that shows the product being unpacked or used for the first time.",
    "Ask your followers a question that your product helps with, and reply to every answer.",
]


def template_marketing(req: MarketingRequest) -> MarketingResponse:
    """Rule-based draft, always labelled as template-based. Used only when the person chooses it."""
    copy = RuleBasedProvider().generate(
        CopyRequest(
            product_name=req.product_name,
            category=_CATEGORY_LABEL.get(req.category, "Other"),
            description=req.description,
            target_audience=req.target_audience,
            brand_name=req.brand_name,
            offer=req.offer,
            tone=_TONE_TO_COPY[req.tone],
            style=_STYLE_FOR_TONE.get(req.tone, "minimal"),
        )
    )
    promo = next((p.text for p in copy.promos if p.kind == "ad"), None) or (copy.promos[0].text if copy.promos else None)
    full = MarketingContent(
        captions=[c.text for c in copy.captions[:3]],
        hashtags=copy.hashtags[:HASHTAG_MAX],
        headlines=[p.text for p in copy.promos if p.kind == "headline"][:5],
        description=copy.short_descriptions[0] if copy.short_descriptions else None,
        ctas=copy.ctas[:3],
        promo=promo,
        ideas=list(_TEMPLATE_IDEAS),
    )
    keep = SECTION_NAMES if req.section == "all" else (req.section,)
    content = MarketingContent(**{k: v for k, v in full.model_dump().items() if k in keep})
    return MarketingResponse(source=TEMPLATE_SOURCE, section=req.section, content=content, warnings=[])
