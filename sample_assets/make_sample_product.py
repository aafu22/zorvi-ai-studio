"""Draws the demo product image (sample-product.jpg) with Pillow.

The image is an illustration created for this project, so it has no third-party licence.
Run from anywhere:   python make_sample_product.py
Output:              sample-product.jpg (next to this script), 1600 x 1600
Fonts:               ../backend/assets/fonts (SIL Open Font Licence)
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "backend" / "assets" / "fonts"
OUT = HERE / "sample-product.jpg"

FINAL = 1600
S = 2  # draw at 2x, then shrink for smooth edges
W = H = FINAL * S


def px(v: float) -> int:
    return round(v * S)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vertical_gradient(size, top, bottom):
    w, h = size
    column = Image.new("RGB", (1, h))
    column.putdata([lerp(top, bottom, y / max(1, h - 1)) for y in range(h)])
    return column.resize((w, h))


def horizontal_ramp(size, stops):
    """Left-to-right colour ramp through evenly spaced colour stops."""
    w, h = size
    row = Image.new("RGB", (w, 1))
    n = len(stops) - 1
    colours = []
    for x in range(w):
        t = x / max(1, w - 1) * n
        i = min(int(t), n - 1)
        colours.append(lerp(stops[i], stops[i + 1], t - i))
    row.putdata(colours)
    return row.resize((w, h))


def rounded_mask(size, radius):
    big = Image.new("L", (size[0] * 2, size[1] * 2), 0)
    ImageDraw.Draw(big).rounded_rectangle([0, 0, size[0] * 2 - 1, size[1] * 2 - 1], radius=radius * 2, fill=255)
    return big.resize(size, Image.Resampling.LANCZOS)


def font(name: str, size: float):
    return ImageFont.truetype(str(FONTS / name), px(size))


def centered(draw, text, fnt, cx, y, fill, tracking=0):
    """Draw text centred on cx. cx and y are in design units (scaled by S here); tracking is in pixels."""
    widths = [draw.textlength(ch, font=fnt) + tracking for ch in text]
    x = px(cx) - (sum(widths) - tracking) / 2
    for ch, w in zip(text, widths):
        draw.text((x, px(y)), ch, font=fnt, fill=fill)
        x += w


def main() -> None:
    img = vertical_gradient((W, H), (244, 229, 211), (226, 197, 171))
    table_top = px(1130)

    # table surface
    table = vertical_gradient((W, H - table_top), (219, 184, 152), (196, 158, 126))
    img.paste(table, (0, table_top))
    ImageDraw.Draw(img).line([(0, table_top), (W, table_top)], fill=(236, 212, 188), width=px(3))

    # soft window light and bokeh in the background
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([px(-200), px(-300), px(900), px(700)], fill=(255, 246, 232, 120))
    for cx, cy, r, a in [(1320, 330, 120, 60), (1180, 520, 70, 50), (1430, 600, 90, 40), (230, 760, 80, 45)]:
        gd.ellipse([px(cx - r), px(cy - r), px(cx + r), px(cy + r)], fill=(255, 238, 214, a))
    img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(px(40)))).convert("RGB")

    # contact shadow under the jar
    cx = FINAL // 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([px(cx - 360), px(1130), px(cx + 380), px(1235)], fill=(70, 40, 20, 150))
    img = Image.alpha_composite(img.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(px(28)))).convert("RGB")

    # jar (amber glass): horizontal lighting ramp clipped to a rounded rectangle
    jar_w, jar_h = 600, 560
    jx0, jy0 = cx - jar_w // 2, 1180 - jar_h
    jar_size = (px(jar_w), px(jar_h))
    jar = horizontal_ramp(jar_size, [(150, 78, 24), (214, 128, 44), (238, 168, 78), (200, 112, 36), (132, 66, 20)])
    img.paste(jar, (px(jx0), px(jy0)), rounded_mask(jar_size, 70))

    # wax inside the jar
    inset = 34
    wax_size = (px(jar_w - 2 * inset), px(jar_h - 110 - inset))
    wax = horizontal_ramp(wax_size, [(236, 214, 170), (250, 236, 200), (240, 222, 182), (222, 198, 152)])
    img.paste(wax, (px(jx0 + inset), px(jy0 + 110)), rounded_mask(wax_size, 46))

    d = ImageDraw.Draw(img, "RGBA")
    # wax surface (top ellipse) and wick
    d.ellipse([px(jx0 + inset + 8), px(jy0 + 86), px(jx0 + jar_w - inset - 8), px(jy0 + 138)], fill=(252, 240, 208))
    d.ellipse([px(cx - 14), px(jy0 + 106), px(cx + 14), px(jy0 + 120)], fill=(120, 84, 52))
    d.line([(px(cx), px(jy0 + 112)), (px(cx + 2), px(jy0 + 52))], fill=(48, 36, 30), width=px(7))

    # flame: blurred glow, then outer and inner teardrops
    flame_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(flame_glow).ellipse([px(cx - 150), px(jy0 - 140), px(cx + 150), px(jy0 + 70)], fill=(255, 200, 110, 130))
    img = Image.alpha_composite(img.convert("RGBA"), flame_glow.filter(ImageFilter.GaussianBlur(px(46)))).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon(
        [(px(cx + 2), px(jy0 - 118)), (px(cx + 30), px(jy0 - 52)), (px(cx + 26), px(jy0 + 14)),
         (px(cx + 2), px(jy0 + 54)), (px(cx - 24), px(jy0 + 14)), (px(cx - 28), px(jy0 - 52))],
        fill=(250, 156, 50),
    )
    d.ellipse([px(cx - 30), px(jy0 - 60), px(cx + 30), px(jy0 + 54)], fill=(250, 160, 52))
    d.ellipse([px(cx - 15), px(jy0 - 18), px(cx + 15), px(jy0 + 50)], fill=(255, 236, 160))

    # label
    lw, lh = 400, 280
    lx0, ly0 = cx - lw // 2, jy0 + 190
    label_size = (px(lw), px(lh))
    img.paste(Image.new("RGB", label_size, (250, 243, 230)), (px(lx0), px(ly0)), rounded_mask(label_size, 22))
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle([px(lx0 + 14), px(ly0 + 14), px(lx0 + lw - 14), px(ly0 + lh - 14)], radius=px(12),
                        outline=(176, 110, 52, 255), width=px(3))
    ink, accent = (92, 52, 28), (176, 110, 52)
    centered(d, "HEARTH & HONEY", font("InstrumentSans-Bold.ttf", 25), cx, ly0 + 42, accent, tracking=px(3))
    centered(d, "Amber Glow", font("Lora-Bold.ttf", 54), cx, ly0 + 90, ink)
    d.line([(px(cx - 60), px(ly0 + 178)), (px(cx + 60), px(ly0 + 178))], fill=accent, width=px(3))
    centered(d, "SOY WAX CANDLE", font("InstrumentSans-Bold.ttf", 26), cx, ly0 + 196, ink, tracking=px(3))
    centered(d, "200 g", font("InstrumentSans-Regular.ttf", 24), cx, ly0 + 232, accent)

    # glass highlights
    hl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.rounded_rectangle([px(jx0 + 44), px(jy0 + 90), px(jx0 + 74), px(jy0 + jar_h - 70)], radius=px(14), fill=(255, 245, 225, 120))
    hd.rounded_rectangle([px(jx0 + jar_w - 70), px(jy0 + 120), px(jx0 + jar_w - 56), px(jy0 + jar_h - 110)], radius=px(8), fill=(255, 245, 225, 60))
    img = Image.alpha_composite(img.convert("RGBA"), hl.filter(ImageFilter.GaussianBlur(px(3)))).convert("RGB")

    img = img.resize((FINAL, FINAL), Image.Resampling.LANCZOS)
    img.save(OUT, format="JPEG", quality=92, optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
