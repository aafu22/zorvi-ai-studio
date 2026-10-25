"use client";

import { Check, Clock, Download, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { CopyButton } from "@/components/CopyButton";
import { ExportPanel } from "@/components/ExportPanel";
import { GraphicStudio } from "@/components/GraphicStudio";
import { processImage } from "@/lib/api";
import { formatCopyAsText } from "@/lib/copy-format";
import { useCreateFlow } from "@/lib/create-flow";

export function ReviewStep() {
  const { image, opts, details, style, copy } = useCreateFlow();
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!image) return;
    const controller = new AbortController();
    let objectUrl: string | null = null;
    processImage(image.id, opts, controller.signal)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch((e) => {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Could not render the image.");
      });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [image, opts]);

  const ext = opts.output_format === "jpeg" ? "jpg" : "png";

  return (
    <div className="space-y-10">
      <section aria-labelledby="graphic-heading" className="space-y-4">
        <div>
          <h2 id="graphic-heading" className="text-lg font-semibold text-slate-900">
            Social media graphic
          </h2>
          <p className="text-sm text-slate-500">
            Pick a template, edit the text and colours, then download it. This is a layout built
            from your photo and text, not an AI-generated image.
          </p>
        </div>
        <GraphicStudio />
      </section>

      <section aria-labelledby="export-heading" className="space-y-4">
        <h2 id="export-heading" className="text-lg font-semibold text-slate-900">
          Export and save
        </h2>
        <ExportPanel />
      </section>

      <section aria-labelledby="summary-heading" className="grid gap-6 md:grid-cols-2">
        <h2 id="summary-heading" className="sr-only">
          Your other assets
        </h2>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
          <p className="mb-3 text-sm font-semibold text-slate-900">Edited product image</p>
          <div className="flex aspect-square max-h-72 items-center justify-center overflow-hidden rounded-xl bg-slate-100">
            {url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={url} alt="Your edited product image" className="max-h-full max-w-full object-contain" />
            ) : error ? (
              <p className="px-4 text-center text-sm text-red-700">{error}</p>
            ) : (
              <Loader2 className="h-6 w-6 animate-spin text-slate-400" aria-label="Loading preview" />
            )}
          </div>
          {url && (
            <a
              href={url}
              download={`zorvi-${opts.preset}.${ext}`}
              className="mt-3 flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              Download image
            </a>
          )}
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
            <h3 className="text-base font-semibold text-slate-900">{details.product_name}</h3>
            <p className="mt-0.5 text-sm text-slate-500">
              {[details.category, `${style[0].toUpperCase()}${style.slice(1)} style`, `${details.tone} tone`]
                .filter(Boolean)
                .join(" · ")}
            </p>
            <ul className="mt-4 space-y-2 text-sm">
              <Status done label="Edited product image ready to download" />
              <Status done label="Social media graphic (download above)" />
              <Status done={!!copy} label="Captions, hashtags, descriptions and promo copy written" />
              <Status done label="Marketing kit ZIP and project saving (below)" />
            </ul>
          </div>

          {copy && (
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-slate-900">All your text, ready to paste</p>
                <CopyButton text={formatCopyAsText(copy, details)} label="Copy all text" />
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Includes any edits you made in the previous step. Go back a step to change it.
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function Status({ done, label }: { done?: boolean; label: string }) {
  return (
    <li className={`flex items-center gap-2 ${done ? "text-slate-800" : "text-slate-500"}`}>
      {done ? (
        <Check className="h-4 w-4 text-emerald-600" aria-hidden="true" />
      ) : (
        <Clock className="h-4 w-4 text-slate-400" aria-hidden="true" />
      )}
      {label}
    </li>
  );
}
