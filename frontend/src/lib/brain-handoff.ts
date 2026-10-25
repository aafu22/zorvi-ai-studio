import type { CopyDraft } from "@/types/api";

const KEY = "zorvi.brain-handoff.v1";

/** Text sent from AI Marketing Brain to the existing creative builder (Create Content, step 5). */
export interface BrainHandoff {
  headline: string;
  subheadline: string;
  cta: string;
  // Used only to fill an EMPTY project, never to overwrite what the person already typed.
  product_name: string;
  description: string;
  brand_name: string;
  offer: string;
  target_audience: string;
  copy: CopyDraft | null;
}

export function writeBrainHandoff(handoff: BrainHandoff): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(handoff));
  } catch {
    /* storage blocked: nothing to hand over */
  }
}

export function readBrainHandoff(): BrainHandoff | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return null;
    const h = JSON.parse(raw) as Partial<BrainHandoff>;
    if (typeof h !== "object" || h === null) return null;
    const s = (v: unknown) => (typeof v === "string" ? v : "");
    return {
      headline: s(h.headline),
      subheadline: s(h.subheadline),
      cta: s(h.cta),
      product_name: s(h.product_name),
      description: s(h.description),
      brand_name: s(h.brand_name),
      offer: s(h.offer),
      target_audience: s(h.target_audience),
      copy: h.copy && typeof h.copy === "object" ? (h.copy as CopyDraft) : null,
    };
  } catch {
    return null;
  }
}

export function clearBrainHandoff(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
