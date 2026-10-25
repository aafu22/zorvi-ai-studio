"use client";

import { Loader2, RefreshCw, Send, Sparkles, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { CopyButton } from "@/components/CopyButton";
import { generateMarketing, generateMarketingTemplate, getHealth } from "@/lib/api";
import { writeBrainHandoff } from "@/lib/brain-handoff";
import { clip } from "@/lib/graphic-defaults";
import type {
  CopyDraft,
  MarketingBrief,
  MarketingContent,
  MarketingResponse,
  MarketingSection,
  MarketingTone,
  Tone,
} from "@/types/api";

const DEFAULT_BRIEF: MarketingBrief = {
  product_name: "",
  description: "",
  category: "other",
  price: "",
  offer: "",
  target_audience: "",
  brand_name: "",
  goal: "sales",
  platform: "instagram",
  tone: "friendly",
};

const CATEGORIES = [
  ["fashion", "Fashion"],
  ["beauty", "Beauty"],
  ["food", "Food"],
  ["electronics", "Electronics"],
  ["handmade", "Handmade products"],
  ["other", "Other"],
] as const;
const GOALS = [
  ["launch", "Product launch"],
  ["sales", "Increase sales"],
  ["awareness", "Brand awareness"],
  ["seasonal", "Seasonal promotion"],
  ["engagement", "Engagement"],
] as const;
const PLATFORMS = [
  ["instagram", "Instagram"],
  ["facebook", "Facebook"],
  ["whatsapp", "WhatsApp"],
  ["general", "General marketing"],
] as const;
const TONES: MarketingTone[] = ["friendly", "professional", "playful", "elegant", "persuasive", "minimal"];

/** Existing copy tones used by the rest of the app. */
const COPY_TONE: Record<MarketingTone, Tone> = {
  friendly: "friendly",
  professional: "professional",
  playful: "playful",
  elegant: "luxury",
  persuasive: "professional",
  minimal: "professional",
};

const inputClass =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400";

/** Editable copy of the generated content. Hashtags are one string so they are easy to edit. */
interface Draft {
  captions: string[];
  hashtags: string;
  headlines: string[];
  description: string;
  ctas: string[];
  promo: string;
  ideas: string[];
}
const EMPTY_DRAFT: Draft = { captions: [], hashtags: "", headlines: [], description: "", ctas: [], promo: "", ideas: [] };

function merge(draft: Draft, c: MarketingContent): Draft {
  return {
    captions: c.captions ?? draft.captions,
    hashtags: c.hashtags ? c.hashtags.join(" ") : draft.hashtags,
    headlines: c.headlines ?? draft.headlines,
    description: c.description ?? draft.description,
    ctas: c.ctas ?? draft.ctas,
    promo: c.promo ?? draft.promo,
    ideas: c.ideas ?? draft.ideas,
  };
}

function firstSentence(text: string, max: number): string {
  const first = text.trim().split(/(?<=[.!?])\s+/)[0] ?? "";
  return (first.length <= max ? first : clip(first, max)).replace(/[.!?]+$/, "");
}

export function MarketingBrain() {
  const router = useRouter();
  const [brief, setBrief] = useState<MarketingBrief>(DEFAULT_BRIEF);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [source, setSource] = useState<MarketingResponse["source"] | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [busy, setBusy] = useState<MarketingSection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastSection, setLastSection] = useState<MarketingSection>("all");
  const [keyConfigured, setKeyConfigured] = useState<boolean | null>(null);
  const [touched, setTouched] = useState(false);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    getHealth()
      .then((h) => setKeyConfigured(h.capabilities.llm_provider))
      .catch(() => setKeyConfigured(null));
    return () => controller.current?.abort();
  }, []);

  const set = <K extends keyof MarketingBrief>(key: K, value: MarketingBrief[K]) =>
    setBrief((b) => ({ ...b, [key]: value }));

  const hasResult = draft.captions.length > 0 || draft.description !== "";
  const nameMissing = brief.product_name.trim() === "";

  const run = async (section: MarketingSection, mode: "ai" | "template" = "ai") => {
    setTouched(true);
    if (nameMissing) return;
    controller.current?.abort();
    const ctl = new AbortController();
    controller.current = ctl;
    setBusy(section);
    setLastSection(section);
    setError(null);
    try {
      const body = { ...brief, product_name: brief.product_name.trim(), section };
      const res =
        mode === "ai" ? await generateMarketing(body, ctl.signal) : await generateMarketingTemplate(body);
      // A whole-kit run replaces everything; a section run only replaces that section.
      setDraft((d) => merge(section === "all" ? EMPTY_DRAFT : d, res.content));
      setSource(res.source);
      setWarnings((w) => (section === "all" ? res.warnings : [...new Set([...w, ...res.warnings])]));
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  };

  const sendToBuilder = (headline: string, subheadline: string, cta: string) => {
    const copy: CopyDraft = {
      provider: source ?? { id: "gemini", label: "Generated by AI Marketing Brain", is_ai: true },
      captions: draft.captions.map((text) => ({ tone: COPY_TONE[brief.tone], text })),
      hashtags: draft.hashtags,
      short_descriptions: draft.description ? [draft.description] : [],
      promos: [
        ...draft.headlines.slice(0, 1).map((text) => ({ kind: "headline" as const, text })),
        ...(draft.promo ? [{ kind: "ad" as const, text: draft.promo }] : []),
      ],
      ctas: draft.ctas,
    };
    writeBrainHandoff({
      headline,
      subheadline,
      cta,
      product_name: brief.product_name.trim(),
      description: brief.description,
      brand_name: brief.brand_name,
      offer: brief.offer,
      target_audience: brief.target_audience,
      copy,
    });
    router.push("/create");
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">AI Marketing Brain</h1>
        <p className="mt-1 text-sm text-slate-500">
          Turn your product details into marketing content ready to use.
        </p>
      </div>

      {keyConfigured === false && (
        <p role="status" className="flex gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>
            No Gemini API key is set on the backend, so AI generation will not work yet. Add{" "}
            <code className="rounded bg-amber-100 px-1">GEMINI_API_KEY</code> to{" "}
            <code className="rounded bg-amber-100 px-1">backend/.env</code> and restart the backend. The
            template-based version works without a key.
          </span>
        </p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void run("all");
        }}
        className="grid gap-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:grid-cols-2"
      >
        <div className="sm:col-span-2">
          <label htmlFor="mb-name" className="text-sm font-semibold text-slate-900">
            Product name <span className="text-red-600" aria-hidden="true">*</span>
            <span className="sr-only">(required)</span>
          </label>
          <input
            id="mb-name"
            maxLength={80}
            value={brief.product_name}
            onChange={(e) => set("product_name", e.target.value)}
            aria-invalid={touched && nameMissing}
            aria-describedby={touched && nameMissing ? "mb-name-err" : undefined}
            placeholder="e.g. Rose Quartz Ring"
            className={inputClass}
          />
          {touched && nameMissing && (
            <p id="mb-name-err" role="alert" className="mt-1 text-xs text-red-700">
              Enter a product name to generate content.
            </p>
          )}
        </div>

        <div className="sm:col-span-2">
          <label htmlFor="mb-desc" className="text-sm font-semibold text-slate-900">
            Product description
          </label>
          <p className="mt-0.5 text-xs text-slate-500">
            What it is and its main features. Only facts you give here will be used.
          </p>
          <textarea
            id="mb-desc"
            rows={4}
            maxLength={600}
            value={brief.description}
            onChange={(e) => set("description", e.target.value)}
            placeholder="e.g. Sterling silver ring with a rose quartz stone. Sizes 5 to 9."
            className={inputClass}
          />
          <p className="mt-1 text-right text-xs text-slate-400">{brief.description.length}/600</p>
        </div>

        <Select id="mb-cat" label="Category" value={brief.category} options={CATEGORIES} onChange={(v) => set("category", v)} />
        <Field id="mb-audience" label="Target audience" max={120} value={brief.target_audience} onChange={(v) => set("target_audience", v)} placeholder="e.g. women who love minimal jewellery" />
        <Field id="mb-price" label="Price (optional)" max={40} value={brief.price} onChange={(v) => set("price", v)} placeholder="e.g. ₹1,499" />
        <Field id="mb-offer" label="Offer (optional)" max={80} value={brief.offer} onChange={(v) => set("offer", v)} placeholder="e.g. 20% off this weekend" />
        <Field id="mb-brand" label="Brand name (optional)" max={60} value={brief.brand_name} onChange={(v) => set("brand_name", v)} placeholder="e.g. Luna Studio" />
        <Select id="mb-goal" label="Marketing goal" value={brief.goal} options={GOALS} onChange={(v) => set("goal", v)} />
        <Select id="mb-platform" label="Content platform" value={brief.platform} options={PLATFORMS} onChange={(v) => set("platform", v)} />

        <div>
          <label htmlFor="mb-tone" className="text-sm font-semibold text-slate-900">
            Writing tone
          </label>
          <select id="mb-tone" value={brief.tone} onChange={(e) => set("tone", e.target.value as MarketingTone)} className={`${inputClass} capitalize`}>
            {TONES.map((t) => (
              <option key={t} value={t}>
                {t[0].toUpperCase() + t.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={busy !== null}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto"
          >
            {busy === "all" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Sparkles className="h-4 w-4" aria-hidden="true" />}
            {busy === "all" ? "Generating…" : "Generate Marketing Kit"}
          </button>
        </div>
      </form>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p>{error}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void run(lastSection)}
              disabled={busy !== null}
              className="inline-flex items-center gap-1.5 rounded-lg bg-red-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-800 disabled:opacity-60"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
              Try again
            </button>
            <button
              type="button"
              onClick={() => void run(lastSection, "template")}
              disabled={busy !== null}
              className="rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-800 hover:bg-red-100 disabled:opacity-60"
            >
              Use template-based draft instead (not AI)
            </button>
          </div>
        </div>
      )}

      {busy === "all" && !hasResult && (
        <div className="space-y-3" aria-busy="true" aria-label="Generating your marketing kit">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-24 animate-pulse rounded-2xl bg-slate-200" />
          ))}
        </div>
      )}

      {!hasResult && busy === null && !error && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
          <p className="text-sm font-semibold text-slate-900">Your marketing kit will appear here</p>
          <p className="mt-1 text-sm text-slate-500">
            Fill in the form and choose Generate Marketing Kit. You can edit every result afterwards.
          </p>
        </div>
      )}

      {hasResult && source && (
        <section aria-label="Generated marketing kit" className="space-y-4">
          <p
            className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${
              source.is_ai ? "bg-brand-50 text-brand-700" : "bg-slate-200 text-slate-700"
            }`}
          >
            {source.is_ai ? `AI-generated${source.model ? ` · ${source.model}` : ""}` : "Template-based, not AI-generated"}
          </p>

          {warnings.length > 0 && (
            <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <p className="font-semibold">Check before posting</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-5">
                {warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          <ListCard title="Captions" section="captions" items={draft.captions} onChange={(v) => setDraft((d) => ({ ...d, captions: v }))} busy={busy} onRegenerate={run} rows={4} />
          <TextCard title="Hashtags" section="hashtags" value={draft.hashtags} onChange={(v) => setDraft((d) => ({ ...d, hashtags: v }))} busy={busy} onRegenerate={run} rows={3} />
          <ListCard title="Marketing headlines" section="headlines" items={draft.headlines} onChange={(v) => setDraft((d) => ({ ...d, headlines: v }))} busy={busy} onRegenerate={run} rows={1} />
          <TextCard title="Product description" section="description" value={draft.description} onChange={(v) => setDraft((d) => ({ ...d, description: v }))} busy={busy} onRegenerate={run} rows={4} />
          <ListCard title="Calls to action" section="ctas" items={draft.ctas} onChange={(v) => setDraft((d) => ({ ...d, ctas: v }))} busy={busy} onRegenerate={run} rows={1} />
          <TextCard title="Promotional copy" section="promo" value={draft.promo} onChange={(v) => setDraft((d) => ({ ...d, promo: v }))} busy={busy} onRegenerate={run} rows={3} />
          <ListCard title="Content ideas" section="ideas" items={draft.ideas} onChange={(v) => setDraft((d) => ({ ...d, ideas: v }))} busy={busy} onRegenerate={run} rows={2} />

          <SendPanel draft={draft} onSend={sendToBuilder} />
        </section>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ pieces */

function Field({ id, label, value, onChange, max, placeholder }: { id: string; label: string; value: string; onChange: (v: string) => void; max: number; placeholder?: string }) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-semibold text-slate-900">
        {label}
      </label>
      <input id={id} maxLength={max} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className={inputClass} />
    </div>
  );
}

function Select<T extends string>({ id, label, value, options, onChange }: { id: string; label: string; value: T; options: readonly (readonly [T, string])[]; onChange: (v: T) => void }) {
  return (
    <div>
      <label htmlFor={id} className="text-sm font-semibold text-slate-900">
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value as T)} className={inputClass}>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </div>
  );
}

type RegenerateFn = (section: MarketingSection) => Promise<void>;

function CardShell({ title, section, copyText, busy, onRegenerate, children }: { title: string; section: MarketingSection; copyText: string; busy: MarketingSection | null; onRegenerate: RegenerateFn; children: ReactNode }) {
  const regenerating = busy === section;
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        <div className="flex gap-2">
          <CopyButton text={copyText} label={`Copy ${title.toLowerCase()}`} />
          <button
            type="button"
            onClick={() => void onRegenerate(section)}
            disabled={busy !== null}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {regenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />}
            Regenerate
          </button>
        </div>
      </div>
      <div className="mt-3 space-y-3">{children}</div>
    </div>
  );
}

function TextCard({ title, section, value, onChange, busy, onRegenerate, rows }: { title: string; section: MarketingSection; value: string; onChange: (v: string) => void; busy: MarketingSection | null; onRegenerate: RegenerateFn; rows: number }) {
  return (
    <CardShell title={title} section={section} copyText={value} busy={busy} onRegenerate={onRegenerate}>
      <textarea aria-label={`${title} (editable)`} rows={rows} value={value} onChange={(e) => onChange(e.target.value)} className={inputClass} />
    </CardShell>
  );
}

function ListCard({ title, section, items, onChange, busy, onRegenerate, rows }: { title: string; section: MarketingSection; items: string[]; onChange: (v: string[]) => void; busy: MarketingSection | null; onRegenerate: RegenerateFn; rows: number }) {
  return (
    <CardShell title={title} section={section} copyText={items.join("\n\n")} busy={busy} onRegenerate={onRegenerate}>
      {items.map((item, i) => (
        <div key={i} className="flex items-start gap-2">
          <textarea
            aria-label={`${title} option ${i + 1} (editable)`}
            rows={rows}
            value={item}
            onChange={(e) => onChange(items.map((x, j) => (j === i ? e.target.value : x)))}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
          />
          <CopyButton text={item} label="Copy" />
        </div>
      ))}
    </CardShell>
  );
}

/** Picks which generated text goes into the existing creative builder's headline, subheadline and button. */
function SendPanel({ draft, onSend }: { draft: Draft; onSend: (headline: string, subheadline: string, cta: string) => void }) {
  const [headline, setHeadline] = useState(0);
  const [sub, setSub] = useState<"promo" | "description" | "none">("promo");
  const [cta, setCta] = useState(0);

  const headlineText = clip(draft.headlines[headline] ?? "", 60);
  const subText =
    sub === "none" ? "" : clip(firstSentence(sub === "promo" ? draft.promo : draft.description, 120), 120);
  const ctaText = clip(draft.ctas[cta] ?? "", 30);

  return (
    <div className="rounded-2xl border border-brand-200 bg-brand-50/50 p-5">
      <h2 className="text-base font-semibold text-slate-900">Send to the creative builder</h2>
      <p className="mt-1 text-xs text-slate-600">
        Fills only the headline, subheadline and button text of your social graphic. Your photo, colours
        and template are not changed. Text is shortened to fit.
      </p>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <div>
          <label htmlFor="sp-h" className="text-xs font-semibold text-slate-700">Headline</label>
          <select id="sp-h" value={headline} onChange={(e) => setHeadline(Number(e.target.value))} className={inputClass}>
            {draft.headlines.map((h, i) => (
              <option key={i} value={i}>{clip(h, 40)}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="sp-s" className="text-xs font-semibold text-slate-700">Subheadline</label>
          <select id="sp-s" value={sub} onChange={(e) => setSub(e.target.value as typeof sub)} className={inputClass}>
            <option value="promo">From promotional copy</option>
            <option value="description">From product description</option>
            <option value="none">Leave empty</option>
          </select>
        </div>
        <div>
          <label htmlFor="sp-c" className="text-xs font-semibold text-slate-700">Button text</label>
          <select id="sp-c" value={cta} onChange={(e) => setCta(Number(e.target.value))} className={inputClass}>
            {draft.ctas.map((c, i) => (
              <option key={i} value={i}>{clip(c, 30)}</option>
            ))}
          </select>
        </div>
      </div>
      <p className="mt-3 text-xs text-slate-600">
        Preview: <strong>{headlineText || "(no headline)"}</strong>
        {subText && <> · {subText}</>}
        {ctaText && <> · [{ctaText}]</>}
      </p>
      <button
        type="button"
        onClick={() => onSend(headlineText, subText, ctaText)}
        disabled={!headlineText}
        className="mt-4 inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
      >
        <Send className="h-4 w-4" aria-hidden="true" />
        Send to creative builder
      </button>
    </div>
  );
}
