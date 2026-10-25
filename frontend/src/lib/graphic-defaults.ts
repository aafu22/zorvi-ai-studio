import type {
  BrandKit,
  GraphicColors,
  GraphicDraft,
  GraphicFont,
  GraphicSize,
  ProcessOptions,
  ProductDetails,
  Style,
  Tone,
} from "@/types/api";

/** Starting colours for each visual style (they match the swatches on the style step). */
export const STYLE_PALETTES: Record<Style, GraphicColors> = {
  minimal: { background: "#ffffff", text: "#0f172a", accent: "#4f46e5" },
  luxury: { background: "#0b0b0f", text: "#f5f0e1", accent: "#c9a227" },
  aesthetic: { background: "#f5e6e0", text: "#4a3b52", accent: "#8e7a9b" },
  festive: { background: "#7f1d1d", text: "#fde68a", accent: "#f59e0b" },
  vibrant: { background: "#4f46e5", text: "#ffffff", accent: "#22d3ee" },
};

const STYLE_FONT: Record<Style, GraphicFont> = {
  minimal: "sans",
  luxury: "serif",
  aesthetic: "serif",
  festive: "display",
  vibrant: "display",
};

const CTA_BY_TONE: Record<Tone, string> = {
  friendly: "Shop now",
  professional: "Order today",
  luxury: "Discover more",
  playful: "Grab yours",
  festive: "Shop the festive picks",
};

export function clip(text: string, max: number): string {
  const t = text.replace(/\s+/g, " ").trim();
  if (t.length <= max) return t;
  const cut = t.slice(0, max - 1).replace(/\s+\S*$/, "");
  return `${cut || t.slice(0, max - 1)}…`;
}

function firstSentences(text: string, max: number): string {
  const sentences = text.trim().split(/(?<=[.!?])\s+/);
  let out = "";
  for (const s of sentences) {
    const next = `${out} ${s}`.trim();
    if (next.length > max) break;
    out = next;
  }
  return (out || clip(text, max)).replace(/[.!?]+$/, "");
}

/** Turn "20% off this weekend" into a short badge like "20% off". Empty if nothing fits. */
export function badgeFromOffer(offer: string): string {
  const o = offer.trim();
  if (!o) return "";
  const percent = o.match(/(\d{1,3})\s*%\s*off/i);
  if (percent) return `${percent[1]}% off`;
  const amount = o.match(/(?:₹|rs\.?|\$|£|€)\s?\d+[\d,]*\s*off/i);
  if (amount) return amount[0].replace(/\s+/g, " ").trim().slice(0, 14);
  return o.length <= 14 ? o : "";
}

const SIZE_FROM_PRESET: Record<string, GraphicSize> = {
  square: "square",
  portrait: "portrait",
  story: "story",
};

/** Text fields only, derived from the product details. Used for the first draft and "Reset text". */
export function textFromDetails(details: ProductDetails) {
  return {
    headline: clip(details.product_name, 60),
    subheadline: firstSentences(details.description, 120),
    cta: CTA_BY_TONE[details.tone],
    badge: badgeFromOffer(details.offer),
    brand_name: clip(details.brand_name, 40),
  };
}

/** Colours, font and logo from a saved Brand Kit, as a patch for a graphic draft. */
export function brandPatch(brand: BrandKit): Pick<GraphicDraft, "colors" | "font" | "show_logo"> {
  return { colors: { ...brand.colors }, font: brand.font, show_logo: brand.has_logo };
}

/**
 * First draft of a graphic. A configured Brand Kit wins over the style palette, because the
 * point of a Brand Kit is that every graphic looks like your brand.
 */
export function buildGraphicDefaults(
  details: ProductDetails,
  style: Style,
  opts: ProcessOptions,
  brand?: BrandKit | null,
): GraphicDraft {
  const text = textFromDetails(details);
  const useBrand = !!brand?.configured;
  return {
    template: text.badge ? "offer" : "classic",
    size: SIZE_FROM_PRESET[opts.preset] ?? "square",
    font: useBrand ? brand!.font : STYLE_FONT[style],
    ...text,
    brand_name: text.brand_name || (useBrand ? clip(brand!.brand_name, 40) : ""),
    colors: useBrand ? { ...brand!.colors } : { ...STYLE_PALETTES[style] },
    show_logo: useBrand && brand!.has_logo,
    photo: {
      fit: "cover",
      background: opts.background,
      zoom: opts.fit === "cover" ? opts.zoom : 1,
      focus_x: opts.fit === "cover" ? opts.focus_x : 0.5,
      focus_y: opts.fit === "cover" ? opts.focus_y : 0.5,
      brightness: opts.brightness,
      contrast: opts.contrast,
      saturation: opts.saturation,
    },
    output_format: "png",
  };
}

function luminance(hex: string): number {
  const channel = (i: number) => {
    const s = parseInt(hex.slice(i, i + 2), 16) / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}

/** WCAG contrast ratio between two #rrggbb colours (1 to 21). */
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
