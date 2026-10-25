"""Social media graphics from editable templates, drawn with Pillow.

Each template is a plain function that places the photo, a text stack, a call-to-action
pill, an optional badge and the brand name onto a canvas. Layout is computed from the
canvas size, so every template works at 1080x1080, 1080x1350 and 1080x1920.

Honest limits:
- This is template composition, not AI image generation. The photo is only cropped,
  adjusted and placed.
- The bundled fonts cover Latin text (and the rupee sign). Other scripts and emoji
  cannot be drawn, so emoji are stripped from graphic text.
- Story safe zones are approximate: Instagram's interface covers roughly the top and
  bottom 250 px of a story, and the exact amount varies by device.
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from app.core.errors import AppError
from app.schemas.graphics import (
    FontInfo,
    GraphicOptions,
    GraphicRequest,
    SizeInfo,
    TemplateInfo,
)
from app.schemas.images import ProcessRequest
from app.services import image_service

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
FONT_FILES: dict[str, tuple[str, str]] = {
    "sans": ("InstrumentSans-Regular.ttf", "InstrumentSans-Bold.ttf"),
    "serif": ("Lora-Regular.ttf", "Lora-Bold.ttf"),
    "display": ("BricolageGrotesque-Regular.ttf", "BricolageGrotesque-Bold.ttf"),
}
SIZES: dict[str, tuple[int, int]] = {
    "square": (1080, 1080),
    "portrait": (1080, 1350),
    "story": (1080, 1920),
}
STORY_SAFE = (230, 260)  # (top, bottom) pixels kept free of text in stories

OPTIONS = GraphicOptions(
    templates=[
        TemplateInfo(id="classic", label="Classic", description="Photo on top, text below."),
        TemplateInfo(id="overlay", label="Full photo", description="Photo fills the post; text sits on a soft fade."),
        TemplateInfo(id="frame", label="Framed", description="Centred photo with a border and text below."),
        TemplateInfo(id="offer", label="Offer badge", description="Photo on top with a round badge for a discount.", uses_badge=True),
    ],
    sizes=[
        SizeInfo(id="square", label="Square post", width=1080, height=1080),
        SizeInfo(id="portrait", label="Portrait post", width=1080, height=1350),
        SizeInfo(id="story", label="Story", width=1080, height=1920,
                 note="Text stays clear of the top and bottom areas that Instagram usually covers (approximate)."),
    ],
    fonts=[
        FontInfo(id="sans", label="Instrument Sans"),
        FontInfo(id="serif", label="Lora"),
        FontInfo(id="display", label="Bricolage Grotesque"),
    ],
)

Rgb = tuple[int, int, int]

# ---------------------------------------------------------------------------- text helpers

_EMOJI = re.compile("[\U0001F000-\U0001FFFF☀-➿⬀-⯿️‍⃣]")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_text(text: str) -> str:
    """Remove emoji and control characters (the bundled fonts cannot draw them)."""
    text = _CONTROL.sub(" ", _EMOJI.sub("", text))
    return re.sub(r"\s+", " ", text).strip()


def hex_rgb(value: str) -> Rgb:
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _luminance(c: Rgb) -> float:
    def chan(v: int) -> float:
        s = v / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: Rgb, b: Rgb) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable_on(bg: Rgb) -> Rgb:
    """Black or white, whichever has more contrast on `bg` (used for text on the accent colour)."""
    dark, light = (17, 17, 17), (255, 255, 255)
    return dark if contrast_ratio(bg, dark) >= contrast_ratio(bg, light) else light


def mix(a: Rgb, b: Rgb, t: float) -> Rgb:
    """Blend a towards b by t (0 = a, 1 = b)."""
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


@lru_cache(maxsize=96)
def load_font(font_id: str, bold: bool, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_DIR / FONT_FILES[font_id][1 if bold else 0]
    try:
        return ImageFont.truetype(str(path), max(1, size))
    except OSError:
        return ImageFont.load_default(max(1, size))  # keeps working if a font file is missing


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_w: float) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split(" "):
        candidate = f"{line} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_w:
            line = candidate
            continue
        if line:
            lines.append(line)
            line = ""
        while len(word) > 1 and draw.textlength(word, font=font) > max_w:  # break very long words
            cut = len(word)
            while cut > 1 and draw.textlength(word[:cut], font=font) > max_w:
                cut -= 1
            lines.append(word[:cut])
            word = word[cut:]
        line = word
    if line:
        lines.append(line)
    return lines


@dataclass
class TextBlock:
    lines: list[str]
    font: object
    line_h: int

    @property
    def height(self) -> int:
        return len(self.lines) * self.line_h


def fit_text(draw, text: str, font_id: str, bold: bool, box_w: float, box_h: float,
             max_size: int, min_size: int) -> TextBlock | None:
    """Largest font size (between max and min) at which the wrapped text fits the box.

    If it still does not fit at the minimum size, keep the lines that fit and end with an ellipsis.
    """
    if not text or box_w <= 0 or box_h <= 0:
        return None
    size = max(min_size, max_size)
    while True:
        font = load_font(font_id, bold, size)
        line_h = round(size * 1.18)
        lines = wrap_text(draw, text, font, box_w)
        if len(lines) * line_h <= box_h:
            return TextBlock(lines, font, line_h)
        if size <= min_size:
            break
        size = max(min_size, size - max(1, size // 12))
    allowed = max(1, int(box_h // line_h))
    lines = lines[:allowed]
    last = lines[-1]
    while last and draw.textlength(f"{last}…", font=font) > box_w:
        last = last[:-1]
    lines[-1] = f"{last.rstrip()}…"
    return TextBlock(lines, font, line_h)


def draw_lines(draw, block: TextBlock, x: float, y: float, w: float, fill: Rgb, align: str) -> None:
    for i, line in enumerate(block.lines):
        lw = draw.textlength(line, font=block.font)
        lx = x + (w - lw) / 2 if align == "center" else x
        draw.text((lx, y + i * block.line_h), line, font=block.font, fill=fill)


# ---------------------------------------------------------------------------- shape helpers


def _aa_mask(size: tuple[int, int], radius: float) -> Image.Image:
    """Anti-aliased rounded-rectangle mask (drawn at 4x then shrunk)."""
    w, h = size
    big = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=radius * 4, fill=255)
    return big.resize((w, h), Image.Resampling.LANCZOS)


def paste_shape(canvas: Image.Image, box: tuple[int, int, int, int], radius: float, fill: Rgb) -> None:
    x0, y0, x1, y1 = box
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    canvas.paste(fill, (x0, y0, x0 + w, y0 + h), _aa_mask((w, h), min(radius, w / 2, h / 2)))


def paste_photo(canvas: Image.Image, img: Image.Image, rect: tuple[int, int, int, int],
                radius: float, opts: ProcessRequest) -> None:
    x, y, w, h = rect
    framed = image_service.render_frame(img, (w, h), opts)
    canvas.paste(framed, (x, y), _aa_mask((w, h), min(radius, w / 2, h / 2)))


def paste_shadow(canvas: Image.Image, rect: tuple[int, int, int, int], radius: float) -> None:
    x, y, w, h = rect
    pad = 70
    layer = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    ImageDraw.Draw(layer).rounded_rectangle([pad, pad, pad + w, pad + h], radius=radius, fill=255)
    layer = layer.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.30))
    canvas.paste((0, 0, 0), (x - pad, y - pad + 16, x - pad + layer.width, y - pad + 16 + layer.height), layer)


def paste_fade(canvas: Image.Image, top: int, color: Rgb, solid_from: int | None = None) -> None:
    """Fade from transparent (at `top`) to nearly solid `color`.

    The fade reaches full strength at `solid_from` (default: the bottom edge) and stays
    there, so text placed below that line always sits on a strong, readable backdrop.
    """
    w, h = canvas.size
    gh = max(1, h - top)
    ramp_len = max(1, (solid_from if solid_from is not None else h) - top)
    column = Image.new("L", (1, gh))
    column.putdata([int(242 * _smoothstep(min(1.0, i / ramp_len))) for i in range(gh)])
    canvas.paste(color, (0, top, w, top + gh), column.resize((w, gh), Image.Resampling.NEAREST))


def _smoothstep(t: float) -> float:
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------- template context


@dataclass
class Ctx:
    W: int
    H: int
    size: str
    img: Image.Image
    opts: ProcessRequest
    font: str
    headline: str
    sub: str
    cta: str
    badge: str
    brand: str
    bg: Rgb
    text: Rgb
    accent: Rgb
    canvas: Image.Image
    draw: ImageDraw.ImageDraw
    logo: Image.Image | None = None  # Brand Kit logo (RGBA), drawn in the brand row

    @property
    def m(self) -> int:  # outer margin
        return round(self.W * 0.06)

    @property
    def safe(self) -> tuple[int, int]:
        return STORY_SAFE if self.size == "story" else (0, 0)

    @property
    def cta_h(self) -> int:
        return round(self.W * 0.078) if self.cta else 0

    def bounds(self) -> tuple[int, int]:
        """(top, bottom) of the area where text and shapes may go, brand row excluded."""
        top = self.safe[0] + self.m
        bottom = self.H - self.safe[1] - self.m
        if self.brand or self.logo:
            bottom -= self.brand_h + round(self.m * 0.4)
        return top, bottom

    @property
    def brand_h(self) -> int:
        if self.logo:
            return round(self.W * 0.06)
        return round(self.W * 0.026 * 1.3)

    def draw_brand(self, x: int, w: int, align: str, color: Rgb) -> None:
        if not (self.brand or self.logo):
            return
        y = self.H - self.safe[1] - self.m - self.brand_h
        size = round(self.W * 0.026)
        if not self.logo:  # text-only brand row
            block = fit_text(self.draw, self.brand.upper(), self.font, True, w, self.brand_h, size, 14)
            if block:
                draw_lines(self.draw, block, x, y, w, color, align)
            return

        # Logo (and optional brand name beside it), kept together as one group.
        gap = round(self.W * 0.015)
        lh = self.brand_h
        lw = max(1, round(self.logo.width * lh / self.logo.height))
        if lw > w * 0.4:  # very wide logos are limited to 40% of the row
            lw = round(w * 0.4)
            lh = max(1, round(self.logo.height * lw / self.logo.width))
        logo = self.logo.resize((lw, lh), Image.Resampling.LANCZOS)

        block = None
        text_w = 0
        if self.brand:
            block = fit_text(self.draw, self.brand.upper(), self.font, True, w - lw - gap, self.brand_h, size, 14)
            if block:
                text_w = round(max(self.draw.textlength(line, font=block.font) for line in block.lines))
        total = lw + (gap + text_w if block else 0)
        start = x if align == "left" else x + (w - total) // 2
        self.canvas.paste(logo, (start, y + (self.brand_h - lh) // 2), logo)
        if block:
            ty = y + (self.brand_h - block.height) / 2
            draw_lines(self.draw, block, start + lw + gap, ty, text_w, color, "left")

    def draw_stack(self, zone: tuple[int, int, int, int], align: str, text_color: Rgb, sub_color: Rgb) -> None:
        x, y, w, h = zone
        if h < 24 or w < 24:
            return
        gap = round(h * 0.06)
        head = fit_text(self.draw, self.headline, self.font, True, w, h * (0.64 if self.sub else 1.0),
                        round(self.W * 0.1), round(self.W * 0.03))
        used = head.height if head else 0
        sub = None
        if self.sub:
            avail = h - used - (gap if head else 0)
            sub = fit_text(self.draw, self.sub, self.font, False, w, avail,
                           round(self.W * 0.04), round(self.W * 0.022))
        total = used + (sub.height if sub else 0) + (gap if head and sub else 0)
        cy = y + (h - total) / 2
        if head:
            draw_lines(self.draw, head, x, cy, w, text_color, align)
            cy += head.height + gap
        if sub:
            draw_lines(self.draw, sub, x, cy, w, sub_color, align)

    def draw_cta(self, x: int, y: int, w: int, align: str) -> None:
        if not self.cta:
            return
        h = self.cta_h
        pad = round(h * 0.55)
        block = fit_text(self.draw, self.cta, self.font, True, w - 2 * pad, h, round(h * 0.42), 12)
        if not block:
            return
        tw = max(self.draw.textlength(line, font=block.font) for line in block.lines)
        pill_w = min(w, round(tw + 2 * pad))
        px = x if align == "left" else x + (w - pill_w) // 2
        paste_shape(self.canvas, (px, y, px + pill_w, y + h), h / 2, self.accent)
        ty = y + (h - block.line_h * len(block.lines)) / 2
        draw_lines(self.draw, block, px, ty, pill_w, readable_on(self.accent), "center")


# ---------------------------------------------------------------------------- templates


def tpl_classic(c: Ctx) -> None:
    m = c.m
    top, bottom = c.bounds()
    photo_h = round((bottom - top) * 0.60)
    gap = round(m * 0.6)
    paste_photo(c.canvas, c.img, (m, top, c.W - 2 * m, photo_h), m * 0.5, c.opts)
    zone_top = top + photo_h + gap
    zone_bottom = bottom - (c.cta_h + gap if c.cta else 0)
    c.draw_stack((m, zone_top, c.W - 2 * m, zone_bottom - zone_top), "left", c.text, mix(c.text, c.bg, 0.2))
    c.draw_cta(m, bottom - c.cta_h, c.W - 2 * m, "left")
    c.draw_brand(m, c.W - 2 * m, "left", mix(c.text, c.bg, 0.4))


def tpl_overlay(c: Ctx) -> None:
    m = c.m
    framed = image_service.render_frame(c.img, (c.W, c.H), c.opts)
    c.canvas.paste(framed, (0, 0))
    _, bottom = c.bounds()
    gap = round(m * 0.6)
    zone_h = round(c.H * 0.2)
    cta_block = c.cta_h + gap if c.cta else 0
    zone_top = bottom - cta_block - zone_h
    paste_fade(c.canvas, max(0, zone_top - round(c.H * 0.18)), c.bg, solid_from=zone_top + round(c.H * 0.02))
    c.draw_stack((m, zone_top, c.W - 2 * m, zone_h), "left", c.text, mix(c.text, c.bg, 0.2))
    c.draw_cta(m, bottom - c.cta_h, c.W - 2 * m, "left")
    c.draw_brand(m, c.W - 2 * m, "left", mix(c.text, c.bg, 0.35))


def tpl_frame(c: Ctx) -> None:
    m = c.m
    inset = round(m * 0.45)
    c.draw.rectangle([inset, inset, c.W - inset, c.H - inset], outline=c.accent, width=4)
    top, bottom = c.bounds()
    top += round(m * 0.4)
    side = round(m * 1.6)
    photo_h = round((bottom - top) * 0.56)
    rect = (side, top, c.W - 2 * side, photo_h)
    paste_shadow(c.canvas, rect, m * 0.3)
    paste_photo(c.canvas, c.img, rect, m * 0.3, c.opts)
    gap = round(m * 0.6)
    zone_top = top + photo_h + gap
    zone_bottom = bottom - (c.cta_h + gap if c.cta else 0)
    inner_w = c.W - 2 * side
    c.draw_stack((side, zone_top, inner_w, zone_bottom - zone_top), "center", c.text, mix(c.text, c.bg, 0.2))
    c.draw_cta(side, bottom - c.cta_h, inner_w, "center")
    c.draw_brand(side, inner_w, "center", mix(c.text, c.bg, 0.4))


def tpl_offer(c: Ctx) -> None:
    m = c.m
    top, bottom = c.bounds()
    photo_h = round(c.H * 0.54)
    framed = image_service.render_frame(c.img, (c.W, photo_h), c.opts)
    c.canvas.paste(framed, (0, 0))
    if c.badge:
        d = round(c.W * 0.23)
        bx, by = c.W - m - d, c.safe[0] + m
        paste_shape(c.canvas, (bx, by, bx + d, by + d), d / 2, c.accent)
        inner = round(d * 0.72)
        block = fit_text(c.draw, c.badge.upper(), c.font, True, inner, inner, round(d * 0.3), 12)
        if block:
            ty = by + (d - block.height) / 2
            draw_lines(c.draw, block, bx + (d - inner) / 2, ty, inner, readable_on(c.accent), "center")
    gap = round(m * 0.6)
    zone_top = photo_h + gap
    zone_bottom = bottom - (c.cta_h + gap if c.cta else 0)
    c.draw_stack((m, zone_top, c.W - 2 * m, zone_bottom - zone_top), "left", c.text, mix(c.text, c.bg, 0.2))
    c.draw_cta(m, bottom - c.cta_h, c.W - 2 * m, "left")
    c.draw_brand(m, c.W - 2 * m, "left", mix(c.text, c.bg, 0.4))


TEMPLATES = {
    "classic": tpl_classic,
    "overlay": tpl_overlay,
    "frame": tpl_frame,
    "offer": tpl_offer,
}

# ---------------------------------------------------------------------------- entry point


def render_graphic(photo_path: Path, req: GraphicRequest, preview_width: int | None = None,
                   logo_path: Path | None = None) -> tuple[bytes, str]:
    """Render one graphic. The original photo file is only read, never changed.

    With `preview_width`, the finished full-size graphic is scaled down, so the preview has
    exactly the same layout as the export (just fewer pixels to send).
    The Brand Kit logo is drawn only when `req.show_logo` is set and `logo_path` points to a file.
    """
    try:
        with Image.open(photo_path) as src:
            img = ImageOps.exif_transpose(src).convert("RGBA")
    except Exception as exc:
        raise AppError(400, "The stored image could not be read.") from exc

    logo = None
    if req.show_logo and logo_path is not None:
        try:
            with Image.open(logo_path) as raw:
                logo = raw.convert("RGBA")
        except Exception:
            logo = None  # a missing or unreadable logo must never break the graphic

    W, H = SIZES[req.size]
    bg = hex_rgb(req.colors.background)
    canvas = Image.new("RGB", (W, H), bg)
    p = req.photo
    opts = ProcessRequest(
        preset="square", fit=p.fit, background=p.background, zoom=p.zoom,
        focus_x=p.focus_x, focus_y=p.focus_y, brightness=p.brightness,
        contrast=p.contrast, saturation=p.saturation,
    )
    ctx = Ctx(
        W=W, H=H, size=req.size, img=img, opts=opts, font=req.font,
        headline=sanitize_text(req.headline), sub=sanitize_text(req.subheadline),
        cta=sanitize_text(req.cta), badge=sanitize_text(req.badge), brand=sanitize_text(req.brand_name),
        bg=bg, text=hex_rgb(req.colors.text), accent=hex_rgb(req.colors.accent),
        canvas=canvas, draw=ImageDraw.Draw(canvas), logo=logo,
    )
    TEMPLATES[req.template](ctx)
    if preview_width and preview_width < W:
        canvas = canvas.resize((preview_width, round(H * preview_width / W)), Image.Resampling.LANCZOS)
    return image_service.encode(canvas, req.output_format)
