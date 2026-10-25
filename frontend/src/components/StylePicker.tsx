"use client";

import { useCreateFlow } from "@/lib/create-flow";
import type { Style } from "@/types/api";

const STYLES: { value: Style; label: string; description: string; colors: string[] }[] = [
  { value: "minimal", label: "Minimal", description: "Clean, airy, lots of white space.", colors: ["#ffffff", "#e2e8f0", "#0f172a"] },
  { value: "luxury", label: "Luxury", description: "Dark tones with gold accents.", colors: ["#0b0b0f", "#c9a227", "#f5f0e1"] },
  { value: "aesthetic", label: "Aesthetic", description: "Soft, muted, dreamy palette.", colors: ["#f5e6e0", "#d9b8c4", "#8e7a9b"] },
  { value: "festive", label: "Festive", description: "Warm reds and golds for celebrations.", colors: ["#7f1d1d", "#f59e0b", "#fde68a"] },
  { value: "vibrant", label: "Vibrant", description: "Bold, saturated colour pops.", colors: ["#ec4899", "#6366f1", "#22d3ee"] },
];

export function StylePicker() {
  const { style, setStyle } = useCreateFlow();

  return (
    <div className="space-y-4">
      <fieldset>
        <legend className="sr-only">Visual style</legend>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {STYLES.map((s) => (
            <label
              key={s.value}
              className={`cursor-pointer rounded-2xl border bg-white p-4 shadow-card has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500 ${
                style === s.value ? "border-brand-500 ring-2 ring-brand-500" : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <input
                type="radio"
                name="style"
                className="sr-only"
                checked={style === s.value}
                onChange={() => setStyle(s.value)}
              />
              <span className="flex h-14 overflow-hidden rounded-lg border border-slate-200" aria-hidden="true">
                {s.colors.map((c) => (
                  <span key={c} className="flex-1" style={{ backgroundColor: c }} />
                ))}
              </span>
              <span className="mt-3 block text-sm font-semibold text-slate-900">{s.label}</span>
              <span className="mt-0.5 block text-xs text-slate-500">{s.description}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <p className="text-sm text-slate-500">
        Your style shapes the hashtag mix and sets the starting colours and font of your social
        graphic. You can change any of them later.
      </p>
    </div>
  );
}
