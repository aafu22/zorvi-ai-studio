"use client";

import { Check, Loader2, RotateCcw, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AuthedImage } from "@/components/AuthedImage";
import { TONES } from "@/components/DetailsForm";
import {
  ApiError,
  BRAND_LOGO_PATH,
  deleteLogo,
  getBrandKit,
  resetBrandKit,
  saveBrandKit,
  uploadLogo,
} from "@/lib/api";
import { STYLE_PALETTES, contrastRatio } from "@/lib/graphic-defaults";
import type { BrandKit, BrandKitInput, GraphicFont } from "@/types/api";

const FONTS: { value: GraphicFont; label: string }[] = [
  { value: "sans", label: "Sans (Instrument Sans)" },
  { value: "serif", label: "Serif (Lora)" },
  { value: "display", label: "Display (Bricolage Grotesque)" },
];

const EMPTY: BrandKitInput = {
  brand_name: "",
  colors: { ...STYLE_PALETTES.minimal },
  font: "sans",
  tone: "friendly",
};

const MAX_LOGO_MB = 2;
const inputClass =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400";

function errorText(e: unknown): string {
  return e instanceof ApiError || e instanceof Error ? e.message : "Something went wrong.";
}

export function BrandKitEditor() {
  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [form, setForm] = useState<BrandKitInput>(EMPTY);
  const [saved, setSaved] = useState<BrandKit | null>(null);
  const [logoVersion, setLogoVersion] = useState(0);
  const [busy, setBusy] = useState<"save" | "logo" | "reset" | null>(null);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getBrandKit()
      .then((kit) => {
        setSaved(kit);
        if (kit.configured) {
          setForm({ brand_name: kit.brand_name, colors: kit.colors, font: kit.font, tone: kit.tone });
        }
      })
      .catch((e) => setLoadError(errorText(e)))
      .finally(() => setLoaded(true));
  }, []);

  const setColor = (key: keyof BrandKitInput["colors"], value: string) =>
    setForm((f) => ({ ...f, colors: { ...f.colors, [key]: value } }));

  const dirty =
    !saved?.configured ||
    JSON.stringify(form) !==
      JSON.stringify({ brand_name: saved.brand_name, colors: saved.colors, font: saved.font, tone: saved.tone });

  const save = async () => {
    setBusy("save");
    setMessage(null);
    try {
      setSaved(await saveBrandKit({ ...form, brand_name: form.brand_name.trim() }));
      setMessage({ kind: "ok", text: "Brand Kit saved. New graphics will use it." });
    } catch (e) {
      setMessage({ kind: "error", text: errorText(e) });
    } finally {
      setBusy(null);
    }
  };

  const reset = async () => {
    if (!window.confirm("Reset your Brand Kit? This removes your saved colours, font, tone and logo.")) return;
    setBusy("reset");
    setMessage(null);
    try {
      await resetBrandKit();
      setSaved(await getBrandKit());
      setForm(EMPTY);
      setMessage({ kind: "ok", text: "Brand Kit reset." });
    } catch (e) {
      setMessage({ kind: "error", text: errorText(e) });
    } finally {
      setBusy(null);
    }
  };

  const onLogo = async (file: File | undefined) => {
    if (!file) return;
    if (file.size > MAX_LOGO_MB * 1024 * 1024) {
      setMessage({ kind: "error", text: `That logo is larger than ${MAX_LOGO_MB} MB.` });
      return;
    }
    setBusy("logo");
    setMessage(null);
    try {
      setSaved(await uploadLogo(file));
      setLogoVersion((v) => v + 1);
      setMessage({ kind: "ok", text: "Logo uploaded." });
    } catch (e) {
      setMessage({ kind: "error", text: errorText(e) });
    } finally {
      setBusy(null);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const removeLogo = async () => {
    setBusy("logo");
    setMessage(null);
    try {
      setSaved(await deleteLogo());
      setMessage({ kind: "ok", text: "Logo removed." });
    } catch (e) {
      setMessage({ kind: "error", text: errorText(e) });
    } finally {
      setBusy(null);
    }
  };

  if (!loaded) {
    return <div className="h-64 animate-pulse rounded-2xl bg-slate-200" aria-busy="true" />;
  }

  const ratio = contrastRatio(form.colors.background, form.colors.text);
  const lowContrast = ratio < 4.5;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Brand Kit</h1>
        <p className="mt-1 text-sm text-slate-500">
          Set your brand once. New projects start with your brand name and tone, and the graphic
          studio can apply your colours, font and logo in one click.
        </p>
      </div>

      {loadError && (
        <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          Could not load your Brand Kit: {loadError}. You can still edit the form, but saving needs the
          backend running.
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <div>
            <label htmlFor="bk-name" className="text-sm font-semibold text-slate-900">
              Brand name
            </label>
            <input
              id="bk-name"
              maxLength={60}
              value={form.brand_name}
              onChange={(e) => setForm((f) => ({ ...f, brand_name: e.target.value }))}
              placeholder="e.g. Luna Studio"
              className={inputClass}
            />
          </div>

          <fieldset>
            <legend className="text-sm font-semibold text-slate-900">Colours</legend>
            <div className="mt-2 grid grid-cols-3 gap-3">
              {(
                [
                  ["background", "Background"],
                  ["text", "Text"],
                  ["accent", "Accent"],
                ] as const
              ).map(([key, label]) => (
                <div key={key}>
                  <label htmlFor={`bk-${key}`} className="block text-xs font-medium text-slate-700">
                    {label}
                  </label>
                  <input
                    id={`bk-${key}`}
                    type="color"
                    value={form.colors[key]}
                    onChange={(e) => setColor(key, e.target.value)}
                    className="mt-1 h-10 w-full cursor-pointer rounded border border-slate-200 bg-white p-0.5"
                  />
                </div>
              ))}
            </div>
            {lowContrast && (
              <p role="status" className="mt-2 text-xs text-amber-700">
                Text on background has a contrast ratio of {ratio.toFixed(1)}:1. Aim for 4.5:1 or more so
                your graphics stay easy to read.
              </p>
            )}
          </fieldset>

          <div>
            <label htmlFor="bk-font" className="text-sm font-semibold text-slate-900">
              Font
            </label>
            <select
              id="bk-font"
              value={form.font}
              onChange={(e) => setForm((f) => ({ ...f, font: e.target.value as GraphicFont }))}
              className={inputClass}
            >
              {FONTS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>

          <fieldset>
            <legend className="text-sm font-semibold text-slate-900">Default tone of voice</legend>
            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-5">
              {TONES.map((t) => (
                <label
                  key={t.value}
                  className={`cursor-pointer rounded-lg border px-3 py-2 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500 ${
                    form.tone === t.value
                      ? "border-brand-500 bg-brand-50 text-brand-700"
                      : "border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="radio"
                    name="bk-tone"
                    className="sr-only"
                    checked={form.tone === t.value}
                    onChange={() => setForm((f) => ({ ...f, tone: t.value }))}
                  />
                  <span className="block font-medium">{t.label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="flex flex-wrap items-center gap-3 border-t border-slate-100 pt-5">
            <button
              type="button"
              onClick={() => void save()}
              disabled={busy !== null || !form.brand_name.trim() || !dirty}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {busy === "save" && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
              Save Brand Kit
            </button>
            {saved?.configured && (
              <button
                type="button"
                onClick={() => void reset()}
                disabled={busy !== null}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
                Reset
              </button>
            )}
            {!form.brand_name.trim() && <span className="text-xs text-slate-500">Enter a brand name to save.</span>}
          </div>

          {message && (
            <p
              role={message.kind === "error" ? "alert" : "status"}
              className={`flex items-center gap-1.5 text-sm ${message.kind === "error" ? "text-red-700" : "text-emerald-700"}`}
            >
              {message.kind === "ok" && <Check className="h-4 w-4" aria-hidden="true" />}
              {message.text}
            </p>
          )}
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
            <h2 className="text-sm font-semibold text-slate-900">Logo</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              PNG, JPG or WebP up to {MAX_LOGO_MB} MB. It is shrunk and shown small on your graphics.
            </p>
            <div className="mt-3 flex h-28 items-center justify-center rounded-xl bg-slate-100">
              {saved?.has_logo ? (
                <AuthedImage
                  path={BRAND_LOGO_PATH}
                  version={logoVersion}
                  alt="Your brand logo"
                  className="max-h-24 max-w-[80%] object-contain"
                />
              ) : (
                <span className="text-xs text-slate-500">No logo yet</span>
              )}
            </div>
            <input
              ref={fileInput}
              id="bk-logo"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              onChange={(e) => void onLogo(e.target.files?.[0])}
            />
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => fileInput.current?.click()}
                className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-60"
              >
                {busy === "logo" ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Upload className="h-4 w-4" aria-hidden="true" />
                )}
                {saved?.has_logo ? "Replace" : "Upload logo"}
              </button>
              {saved?.has_logo && (
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => void removeLogo()}
                  aria-label="Remove logo"
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
            </div>
          </div>

          <div
            className="rounded-2xl border border-slate-200 p-5 shadow-card"
            style={{ backgroundColor: form.colors.background, color: form.colors.text }}
            aria-label="Brand colour preview"
          >
            <p className="text-xs opacity-70">Preview</p>
            <p className="mt-1 text-lg font-bold">{form.brand_name.trim() || "Your brand"}</p>
            <span
              className="mt-3 inline-block rounded-full px-3 py-1 text-xs font-semibold"
              style={{ backgroundColor: form.colors.accent, color: form.colors.background }}
            >
              Shop now
            </span>
          </div>
        </aside>
      </div>
    </div>
  );
}
