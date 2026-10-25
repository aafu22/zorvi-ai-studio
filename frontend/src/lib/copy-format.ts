import type { CopyDraft, ProductDetails } from "@/types/api";

const TONE_LABEL: Record<string, string> = {
  friendly: "Friendly",
  professional: "Professional",
  luxury: "Luxury",
  playful: "Playful",
  festive: "Festive",
};

export const PROMO_LABEL: Record<string, string> = {
  headline: "Headline",
  ad: "Short ad",
  story: "Story text",
};

/** Plain-text version of all copy, for "Copy all". */
export function formatCopyAsText(copy: CopyDraft, details: ProductDetails): string {
  const lines: string[] = [`${details.product_name}`, ""];

  lines.push("CAPTIONS");
  copy.captions.forEach((c, i) => {
    lines.push(`${i + 1}. [${TONE_LABEL[c.tone] ?? c.tone}]`, c.text, "");
  });

  lines.push("HASHTAGS", copy.hashtags.trim(), "");

  lines.push("SHORT DESCRIPTIONS");
  copy.short_descriptions.forEach((d, i) => lines.push(`${i + 1}. ${d}`));
  lines.push("");

  lines.push("PROMOTIONAL COPY");
  copy.promos.forEach((p) => lines.push(`${PROMO_LABEL[p.kind] ?? p.kind}:`, p.text, ""));

  lines.push("CALLS TO ACTION");
  copy.ctas.forEach((c) => lines.push(`- ${c}`));

  return lines.join("\n").trim() + "\n";
}

export { TONE_LABEL };
