"""Image validation and editing with Pillow.

Pipeline for process_image():
  open original (read-only) -> fix EXIF rotation -> crop/resize to the target frame
  -> colour adjustments (on the photo only) -> flatten onto the background colour -> encode.
The original file on disk is only ever read.
"""

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from app.core.errors import AppError
from app.schemas.images import ProcessRequest

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_PIXELS = 40_000_000  # ~40 megapixels; protects memory on an 8 GB machine
MAX_ORIGINAL_SIDE = 4096  # cap for the "original size" preset
PRESETS: dict[str, tuple[int, int]] = {
    "square": (1080, 1080),
    "portrait": (1080, 1350),
    "story": (1080, 1920),
}


@dataclass(frozen=True)
class ImageInfo:
    format: str
    width: int
    height: int


def inspect_image(data: bytes) -> ImageInfo:
    """Check that bytes really are a supported image. Trusts content, not file name or MIME type."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format or ""
            width, height = img.size
            if fmt not in ALLOWED_FORMATS:
                raise AppError(415, "Unsupported image type. Please upload a JPG, PNG or WebP file.")
            if width * height > MAX_PIXELS:
                raise AppError(413, "This image has too many pixels. Please use one under 40 megapixels.")
            img.verify()  # detects truncated/corrupt files without a full decode
    except AppError:
        raise
    except Exception as exc:  # UnidentifiedImageError, DecompressionBombError, OSError, ...
        raise AppError(400, "That file is not a valid image.") from exc
    return ImageInfo(format=fmt, width=width, height=height)


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _cover_crop(img: Image.Image, aspect: float, zoom: float, fx: float, fy: float) -> Image.Image:
    """Crop to the given aspect ratio. zoom>1 crops tighter; fx/fy (0..1) slide the crop window."""
    w, h = img.size
    if w / h > aspect:
        crop_h, crop_w = float(h), h * aspect
    else:
        crop_w, crop_h = float(w), w / aspect
    crop_w = max(1.0, crop_w / zoom)
    crop_h = max(1.0, crop_h / zoom)
    left = fx * (w - crop_w)
    top = fy * (h - crop_h)
    box = (round(left), round(top), round(left + crop_w), round(top + crop_h))
    return img.crop(box)


def _adjust(img: Image.Image, brightness: float, contrast: float, saturation: float) -> Image.Image:
    """Apply adjustments to RGB only, so transparency (alpha) is left untouched."""
    if brightness == 1.0 and contrast == 1.0 and saturation == 1.0:
        return img
    r, g, b, a = img.split()
    rgb = Image.merge("RGB", (r, g, b))
    if brightness != 1.0:
        rgb = ImageEnhance.Brightness(rgb).enhance(brightness)
    if contrast != 1.0:
        rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    if saturation != 1.0:
        rgb = ImageEnhance.Color(rgb).enhance(saturation)
    r, g, b = rgb.split()
    return Image.merge("RGBA", (r, g, b, a))


def render(img: Image.Image, opts: ProcessRequest) -> Image.Image:
    """Core editing step on an RGBA image. Returns an RGB image."""
    bg = _hex_to_rgb(opts.background)
    w, h = img.size

    if opts.preset == "original":
        # Keep the photo's own proportions; only zoom/focus can crop it.
        photo = _cover_crop(img, w / h, opts.zoom, opts.focus_x, opts.focus_y)
        longest = max(photo.size)
        if longest > MAX_ORIGINAL_SIDE:
            scale = MAX_ORIGINAL_SIDE / longest
            photo = photo.resize(
                (max(1, round(photo.width * scale)), max(1, round(photo.height * scale))),
                Image.Resampling.LANCZOS,
            )
        canvas = Image.new("RGB", photo.size, bg)
        photo = _adjust(photo, opts.brightness, opts.contrast, opts.saturation)
        canvas.paste(photo, (0, 0), photo.getchannel("A"))
        return canvas

    return render_frame(img, PRESETS[opts.preset], opts)


def render_frame(img: Image.Image, size: tuple[int, int], opts: ProcessRequest) -> Image.Image:
    """Place a photo into a frame of exactly `size`, using opts.fit / zoom / focus / adjustments.

    Shared by the preset editor and by the graphics templates (photo slots).
    """
    bg = _hex_to_rgb(opts.background)
    w, h = img.size
    tw, th = size
    canvas = Image.new("RGB", (tw, th), bg)
    if opts.fit == "cover":
        photo = _cover_crop(img, tw / th, opts.zoom, opts.focus_x, opts.focus_y)
        photo = photo.resize((tw, th), Image.Resampling.LANCZOS)
        pos = (0, 0)
    else:  # contain
        scale = min(tw / w, th / h)
        size = (max(1, round(w * scale)), max(1, round(h * scale)))
        photo = img.resize(size, Image.Resampling.LANCZOS)
        pos = ((tw - size[0]) // 2, (th - size[1]) // 2)
    photo = _adjust(photo, opts.brightness, opts.contrast, opts.saturation)
    canvas.paste(photo, pos, photo.getchannel("A"))
    return canvas


def encode(img: Image.Image, output_format: str) -> tuple[bytes, str]:
    buf = io.BytesIO()
    if output_format == "jpeg":
        img.save(buf, format="JPEG", quality=92, optimize=True)
        return buf.getvalue(), "image/jpeg"
    img.save(buf, format="PNG")
    return buf.getvalue(), "image/png"


def process_image(path: Path, opts: ProcessRequest) -> tuple[bytes, str]:
    """Render an edited copy of the original. Output has no EXIF/GPS metadata."""
    try:
        with Image.open(path) as src:
            img = ImageOps.exif_transpose(src).convert("RGBA")
    except Exception as exc:
        raise AppError(400, "The stored image could not be read.") from exc
    return encode(render(img, opts), opts.output_format)
