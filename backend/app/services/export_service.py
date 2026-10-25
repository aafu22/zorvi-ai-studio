"""Builds the marketing kit ZIP.

Everything is generated in memory and returned as bytes. File names inside the ZIP are fixed
or built from a fixed vocabulary (template/size names), never from user text, so nothing a
user types can create a path inside the archive. The user's product name is only used,
after slugging, in the download file name.
"""

import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.schemas.export import ExportCopy, ExportDetails, ExportRequest
from app.schemas.graphics import GraphicRequest
from app.schemas.images import ProcessRequest
from app.services import graphics_service, image_service

TONE_LABEL = {
    "friendly": "Friendly", "professional": "Professional", "luxury": "Luxury",
    "playful": "Playful", "festive": "Festive",
}
PROMO_LABEL = {"headline": "Headline", "ad": "Short ad", "story": "Story text"}


def slugify(text: str) -> str:
    """Lower-case ASCII letters, digits and dashes only (safe in file names)."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40].strip("-")
    return slug or "campaign"


def kit_filename(details: ExportDetails) -> str:
    return f"zorvi-{slugify(details.product_name)}-kit.zip"


def copy_to_markdown(details: ExportDetails, copy: ExportCopy) -> str:
    lines = [f"# {details.product_name}", ""]
    meta = [m for m in (details.category, details.brand_name, f"{details.style} style", f"{details.tone} tone") if m]
    lines += [" · ".join(meta), ""]
    origin = "AI model" if copy.provider.is_ai else "templates (not written by an AI model)"
    lines += [f"_Text source: {copy.provider.label}. Assembled from {origin}._", ""]

    lines += ["## Captions", ""]
    for i, c in enumerate(copy.captions, 1):
        lines += [f"### Caption {i} ({TONE_LABEL.get(c.tone, c.tone)})", "", c.text, ""]
    lines += ["## Hashtags", "", copy.hashtags.strip(), ""]
    lines += ["## Short descriptions", ""]
    for i, d in enumerate(copy.short_descriptions, 1):
        lines += [f"{i}. {d}"]
    lines += ["", "## Promotional copy", ""]
    for p in copy.promos:
        lines += [f"### {PROMO_LABEL.get(p.kind, p.kind)}", "", p.text, ""]
    lines += ["## Calls to action", ""]
    lines += [f"- {c}" for c in copy.ctas]
    return "\n".join(lines).rstrip() + "\n"


def description_text(details: ExportDetails, copy: ExportCopy) -> str:
    lines = [details.product_name, ""]
    if details.description:
        lines += ["Your description:", details.description, ""]
    if copy.short_descriptions:
        lines += ["Short product descriptions:", ""]
        for i, d in enumerate(copy.short_descriptions, 1):
            lines += [f"{i}. {d}", ""]
    return "\n".join(lines).rstrip() + "\n"


def readme_text(files: list[str], details: ExportDetails, copy: ExportCopy) -> str:
    source = "written by an AI model" if copy.provider.is_ai else "assembled from templates; no AI model wrote it"
    return (
        f"Zorvi AI Studio marketing kit: {details.product_name}\n"
        f"Created: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n\n"
        "Files\n-----\n" + "\n".join(f"  {f}" for f in files) + "\n\n"
        "Notes\n-----\n"
        f"- The text is {source}. Review it before you post.\n"
        "- Graphics are layouts built from your photo and text, not AI-generated images.\n"
        "- Product images and graphics contain no location (EXIF) data.\n"
    )


def build_kit(photo_path: Path, req: ExportRequest, logo_path: Path | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        names: list[str] = []

        def add(name: str, content: bytes | str) -> None:
            zf.writestr(name, content)
            names.append(name)

        # 1) edited product image
        body, media = image_service.process_image(photo_path, req.edit)
        add(f"images/product-{req.edit.preset}.{'jpg' if media == 'image/jpeg' else 'png'}", body)

        # 2) the same graphic design at each requested size
        for size in req.sizes:
            graphic_req = GraphicRequest(**{**req.graphic.model_dump(), "size": size}, image_id=req.image_id)
            gbody, gmedia = graphics_service.render_graphic(
                photo_path, graphic_req, logo_path=logo_path if graphic_req.show_logo else None
            )
            ext = "jpg" if gmedia == "image/jpeg" else "png"
            add(f"graphics/{req.graphic.template}-{size}.{ext}", gbody)

        # 3) text files
        add("marketing-copy.md", copy_to_markdown(req.details, req.copy_))
        add("product-description.txt", description_text(req.details, req.copy_))

        # 4) optional campaign data
        if req.include_json:
            campaign = {
                "app": get_settings().app_name,
                "app_version": get_settings().app_version,
                "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "details": req.details.model_dump(),
                "copy": {
                    "provider": req.copy_.provider.model_dump(),
                    "captions": [c.model_dump() for c in req.copy_.captions],
                    "hashtags": req.copy_.hashtags,
                    "short_descriptions": req.copy_.short_descriptions,
                    "promos": [p.model_dump() for p in req.copy_.promos],
                    "ctas": req.copy_.ctas,
                },
                "graphic_design": req.graphic.model_dump(),
                "image_edit": req.edit.model_dump(),
                "graphic_sizes": req.sizes,
            }
            add("campaign.json", json.dumps(campaign, indent=2, ensure_ascii=False))

        add("README.txt", readme_text(names + ["README.txt"], req.details, req.copy_))
    return buf.getvalue()
