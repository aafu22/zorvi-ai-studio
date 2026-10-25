"use client";

import { Info, Loader2, RefreshCw, Sparkles, TriangleAlert } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { CopyButton } from "@/components/CopyButton";
import { generateCopy } from "@/lib/api";
import { formatCopyAsText, PROMO_LABEL, TONE_LABEL } from "@/lib/copy-format";
import { useCreateFlow } from "@/lib/create-flow";
import type { CopyDraft } from "@/types/api";

export function CopyStudio() {
  const { details, style, copy, setCopy } = useCreateFlow();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoStarted = useRef(false);

  const generate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await generateCopy({ ...details, style });
      setCopy({ ...res, hashtags: res.hashtags.join(" ") });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate copy.");
    } finally {
      setLoading(false);
    }
  }, [details, style, setCopy]);

  // First visit to this step: generate once automatically.
  useEffect(() => {
    if (!copy && !autoStarted.current) {
      autoStarted.current = true;
      void generate();
    }
  }, [copy, generate]);

  const patch = (fn: (c: CopyDraft) => CopyDraft) => setCopy((c) => (c ? fn(c) : c));
  const setAt = <T,>(list: T[], index: number, value: T) =>
    list.map((item, i) => (i === index ? value : item));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <div className="max-w-xl">
          <p className="flex items-center gap-2 text-sm font-semibold text-slate-900">
            <Sparkles className="h-4 w-4 text-brand-600" aria-hidden="true" />
            {copy ? copy.provider.label : "Marketing copy"}
          </p>
          <p className="mt-1 flex items-start gap-1.5 text-xs text-slate-500">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {copy && copy.provider.is_ai
              ? "Written by an AI model from your details. Review before posting."
              : "Assembled from templates and the details you entered. No AI model is used. Edit anything below; regenerating replaces your edits."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void generate()}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            )}
            {copy ? "Regenerate" : "Generate"}
          </button>
          {copy && <CopyButton text={formatCopyAsText(copy, details)} label="Copy all" />}
        </div>
      </div>

      {error && (
        <p role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}

      {!copy && loading && (
        <div className="space-y-3" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-28 animate-pulse rounded-2xl bg-slate-200" />
          ))}
        </div>
      )}

      {copy && (
        <>
          <Section title="Instagram captions" hint="Three in your chosen tone, plus one in each other tone to compare.">
            {copy.captions.map((c, i) => (
              <Editable
                key={i}
                label={`Caption ${i + 1}`}
                badge={TONE_LABEL[c.tone] ?? c.tone}
                value={c.text}
                onChange={(text) =>
                  patch((d) => ({ ...d, captions: setAt(d.captions, i, { ...c, text }) }))
                }
              />
            ))}
          </Section>

          <Section title="Hashtags" hint="Separate with spaces. Instagram allows up to 30; 5 to 15 is a good range.">
            <Editable
              label="Hashtags"
              value={copy.hashtags}
              onChange={(hashtags) => patch((d) => ({ ...d, hashtags }))}
            />
          </Section>

          <Section title="Short product descriptions">
            {copy.short_descriptions.map((text, i) => (
              <Editable
                key={i}
                label={`Description ${i + 1}`}
                value={text}
                onChange={(v) =>
                  patch((d) => ({ ...d, short_descriptions: setAt(d.short_descriptions, i, v) }))
                }
              />
            ))}
          </Section>

          <Section title="Promotional copy">
            {copy.promos.map((p, i) => (
              <Editable
                key={i}
                label={PROMO_LABEL[p.kind] ?? p.kind}
                badge={PROMO_LABEL[p.kind]}
                value={p.text}
                onChange={(text) =>
                  patch((d) => ({ ...d, promos: setAt(d.promos, i, { ...p, text }) }))
                }
              />
            ))}
          </Section>

          <Section title="Calls to action">
            {copy.ctas.map((text, i) => (
              <Editable
                key={i}
                label={`Call to action ${i + 1}`}
                value={text}
                onChange={(v) => patch((d) => ({ ...d, ctas: setAt(d.ctas, i, v) }))}
              />
            ))}
          </Section>
        </>
      )}
    </div>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-base font-semibold text-slate-900">{title}</h2>
        {hint && <p className="text-xs text-slate-500">{hint}</p>}
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function Editable({
  label,
  badge,
  value,
  onChange,
}: {
  label: string;
  badge?: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const rows = Math.max(2, value.split("\n").length + Math.ceil(value.length / 80));
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="flex items-center gap-2 text-xs font-medium text-slate-600">
          {label}
          {badge && badge !== label && (
            <span className="rounded-full bg-brand-50 px-2 py-0.5 text-[11px] text-brand-700">{badge}</span>
          )}
        </span>
        <CopyButton text={value} />
      </div>
      <textarea
        aria-label={label}
        value={value}
        rows={rows}
        onChange={(e) => onChange(e.target.value)}
        className="w-full resize-y rounded-lg border border-slate-200 px-3 py-2 text-sm leading-relaxed text-slate-900"
      />
    </div>
  );
}
