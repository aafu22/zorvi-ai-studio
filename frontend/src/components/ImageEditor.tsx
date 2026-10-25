"use client";

import {
  Download,
  ImagePlus,
  Loader2,
  RotateCcw,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import {
  deleteImage,
  originalImageUrl,
  processImage,
  uploadImage,
} from "@/lib/api";
import { DemoButton } from "@/components/DemoButton";
import { Slider } from "@/components/Slider";
import { DEFAULT_OPTIONS as DEFAULTS, useCreateFlow } from "@/lib/create-flow";
import type { Fit, OutputFormat, Preset, ProcessOptions } from "@/types/api";

const MAX_UPLOAD_MB = 10; // mirrors the backend default; the server is the real authority
const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];

const PRESETS: { value: Preset; label: string; hint: string }[] = [
  { value: "square", label: "Square post", hint: "1080 × 1080" },
  { value: "portrait", label: "Portrait post", hint: "1080 × 1350" },
  { value: "story", label: "Story", hint: "1080 × 1920" },
  { value: "original", label: "Original size", hint: "keep shape" },
];

const SWATCHES = ["#ffffff", "#f8fafc", "#0f172a", "#fde68a", "#fbcfe8", "#c7d2fe"];

export function ImageEditor() {
  // image + edit settings live in the shared flow state so other steps can use them
  const { image, setImage, opts, setOpts, loadSnapshot } = useCreateFlow();
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const set = <K extends keyof ProcessOptions>(key: K, value: ProcessOptions[K]) =>
    setOpts((o) => ({ ...o, [key]: value }));

  // Re-render the edited preview shortly after the settings change.
  useEffect(() => {
    if (!image) return;
    const controller = new AbortController();
    setProcessing(true);
    const timer = setTimeout(async () => {
      try {
        const blob = await processImage(image.id, opts, controller.signal);
        const url = URL.createObjectURL(blob);
        setResultUrl((old) => {
          if (old) URL.revokeObjectURL(old);
          return url;
        });
        setError(null);
        setProcessing(false);
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Could not process the image.");
        setProcessing(false);
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [image, opts]);

  // Release the last preview URL when leaving the page.
  const urlRef = useRef<string | null>(null);
  urlRef.current = resultUrl;
  useEffect(
    () => () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    },
    [],
  );

  const handleFile = useCallback(async (file: File | undefined) => {
    if (!file) return;
    if (!ACCEPTED.includes(file.type)) {
      setError("Please choose a JPG, PNG or WebP image.");
      return;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`That file is larger than ${MAX_UPLOAD_MB} MB.`);
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const uploaded = await uploadImage(file);
      setResultUrl(null);
      setImage(uploaded);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }, []);

  const removeImage = async () => {
    if (!image) return;
    const id = image.id;
    setImage(null);
    setResultUrl(null);
    setError(null);
    try {
      await deleteImage(id);
    } catch {
      /* it will be cleaned up automatically after the retention period */
    }
  };

  const ext = opts.output_format === "jpeg" ? "jpg" : "png";
  const downloadName = `zorvi-${opts.preset}.${ext}`;
  const adjustedFrom = (o: ProcessOptions) => ({
    brightness: o.brightness,
    contrast: o.contrast,
    saturation: o.saturation,
  });
  const resetAdjustments = () =>
    setOpts((o) => ({
      ...o,
      brightness: DEFAULTS.brightness,
      contrast: DEFAULTS.contrast,
      saturation: DEFAULTS.saturation,
    }));
  const isAdjusted =
    JSON.stringify(adjustedFrom(opts)) !== JSON.stringify(adjustedFrom(DEFAULTS));

  /* ---------------------------------------------------------- upload view */
  if (!image) {
    return (
      <div className="space-y-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            void handleFile(e.dataTransfer.files[0]);
          }}
          className={`flex flex-col items-center rounded-2xl border-2 border-dashed px-6 py-16 text-center transition-colors ${
            dragging ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-white"
          }`}
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">
            {uploading ? (
              <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
            ) : (
              <ImagePlus className="h-6 w-6" aria-hidden="true" />
            )}
          </span>
          <h2 className="mt-4 text-base font-semibold text-slate-900">
            {uploading ? "Uploading…" : "Drop your product photo here"}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            JPG, PNG or WebP, up to {MAX_UPLOAD_MB} MB. Your original is never changed.
          </p>
          <input
            ref={fileInput}
            id="product-file"
            type="file"
            accept={ACCEPTED.join(",")}
            className="sr-only"
            onChange={(e) => void handleFile(e.target.files?.[0])}
          />
          <button
            type="button"
            disabled={uploading}
            onClick={() => fileInput.current?.click()}
            className="mt-6 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            Choose a photo
          </button>
          <p className="mt-4 text-xs text-slate-500">No photo handy?</p>
          <div className="mt-1">
            <DemoButton
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-brand-600 hover:text-brand-700 disabled:opacity-60"
              onLoaded={(demo) =>
                loadSnapshot({ image: demo.image, details: demo.details, style: demo.style, step: 2 })
              }
            >
              Use the demo product
            </DemoButton>
          </div>
        </div>
        {error && <ErrorBanner message={error} />}
      </div>
    );
  }

  /* ---------------------------------------------------------- editor view */
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <figure className="rounded-2xl border border-slate-200 bg-white p-3 shadow-card">
            <figcaption className="mb-2 flex items-center justify-between text-xs font-medium text-slate-500">
              <span>Original</span>
              <span>
                {image.width} × {image.height}
              </span>
            </figcaption>
            <div className="flex aspect-square items-center justify-center overflow-hidden rounded-xl bg-slate-100">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={originalImageUrl(image)}
                alt="Your uploaded product photo"
                className="max-h-full max-w-full object-contain"
              />
            </div>
          </figure>

          <figure className="rounded-2xl border border-slate-200 bg-white p-3 shadow-card">
            <figcaption className="mb-2 text-xs font-medium text-slate-500">
              Edited preview
            </figcaption>
            <div className="relative flex aspect-square items-center justify-center overflow-hidden rounded-xl bg-slate-100">
              {resultUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={resultUrl}
                  alt="Edited version of your product photo"
                  className="max-h-full max-w-full object-contain"
                />
              ) : (
                <div className="h-full w-full animate-pulse bg-slate-200" aria-hidden="true" />
              )}
              {processing && (
                <span
                  role="status"
                  className="absolute right-2 top-2 flex items-center gap-1.5 rounded-full bg-white/90 px-2.5 py-1 text-xs font-medium text-slate-700 shadow"
                >
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                  Updating
                </span>
              )}
            </div>
          </figure>
        </div>

        {error && <ErrorBanner message={error} />}

        <div className="flex flex-wrap items-center gap-3">
          {resultUrl ? (
            <a
              href={resultUrl}
              download={downloadName}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              Download {downloadName}
            </a>
          ) : (
            <span className="inline-flex items-center gap-2 rounded-xl bg-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-500">
              <Download className="h-4 w-4" aria-hidden="true" />
              Download
            </span>
          )}
          <button
            type="button"
            onClick={() => void removeImage()}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            Remove photo
          </button>
        </div>
      </div>

      {/* ---------------------------------------------------------- controls */}
      <aside className="space-y-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <fieldset>
          <legend className="text-sm font-semibold text-slate-900">Size</legend>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {PRESETS.map((p) => (
              <label
                key={p.value}
                className={`cursor-pointer rounded-lg border px-3 py-2 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500 ${
                  opts.preset === p.value
                    ? "border-brand-500 bg-brand-50 text-brand-700"
                    : "border-slate-200 text-slate-700 hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="preset"
                  className="sr-only"
                  checked={opts.preset === p.value}
                  onChange={() => set("preset", p.value)}
                />
                <span className="block font-medium">{p.label}</span>
                <span className="block text-xs text-slate-500">{p.hint}</span>
              </label>
            ))}
          </div>
        </fieldset>

        {opts.preset !== "original" && (
          <fieldset>
            <legend className="text-sm font-semibold text-slate-900">Framing</legend>
            <div className="mt-2 grid grid-cols-2 gap-2">
              {(
                [
                  ["contain", "Fit whole photo"],
                  ["cover", "Fill & crop"],
                ] as [Fit, string][]
              ).map(([value, label]) => (
                <label
                  key={value}
                  className={`cursor-pointer rounded-lg border px-3 py-2 text-center text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500 ${
                    opts.fit === value
                      ? "border-brand-500 bg-brand-50 font-medium text-brand-700"
                      : "border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="radio"
                    name="fit"
                    className="sr-only"
                    checked={opts.fit === value}
                    onChange={() => set("fit", value)}
                  />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
        )}

        {(opts.fit === "cover" || opts.preset === "original") && (
          <fieldset className="space-y-3">
            <legend className="text-sm font-semibold text-slate-900">Crop</legend>
            <Slider
              label="Zoom"
              value={opts.zoom}
              min={1}
              max={4}
              step={0.05}
              display={`${opts.zoom.toFixed(2)}×`}
              onChange={(v) => set("zoom", v)}
            />
            <Slider
              label="Move left / right"
              value={opts.focus_x}
              min={0}
              max={1}
              step={0.01}
              display={`${Math.round(opts.focus_x * 100)}%`}
              disabled={opts.zoom === 1 && opts.preset === "original"}
              onChange={(v) => set("focus_x", v)}
            />
            <Slider
              label="Move up / down"
              value={opts.focus_y}
              min={0}
              max={1}
              step={0.01}
              display={`${Math.round(opts.focus_y * 100)}%`}
              disabled={opts.zoom === 1 && opts.preset === "original"}
              onChange={(v) => set("focus_y", v)}
            />
          </fieldset>
        )}

        <div>
          <label htmlFor="bg-color" className="text-sm font-semibold text-slate-900">
            Background colour
          </label>
          <p className="mt-0.5 text-xs text-slate-500">
            Fills empty space and any transparent areas.
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <input
              id="bg-color"
              type="color"
              value={opts.background}
              onChange={(e) => set("background", e.target.value)}
              className="h-9 w-12 cursor-pointer rounded border border-slate-200 bg-white p-0.5"
            />
            {SWATCHES.map((c) => (
              <button
                key={c}
                type="button"
                aria-label={`Use background ${c}`}
                aria-pressed={opts.background === c}
                onClick={() => set("background", c)}
                style={{ backgroundColor: c }}
                className={`h-7 w-7 rounded-full border ${
                  opts.background === c ? "ring-2 ring-brand-500 ring-offset-1" : "border-slate-300"
                }`}
              />
            ))}
          </div>
        </div>

        <fieldset className="space-y-3">
          <div className="flex items-center justify-between">
            <legend className="text-sm font-semibold text-slate-900">Adjust</legend>
            <button
              type="button"
              onClick={resetAdjustments}
              disabled={!isAdjusted}
              className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 disabled:text-slate-400"
            >
              <RotateCcw className="h-3 w-3" aria-hidden="true" />
              Reset
            </button>
          </div>
          <Slider
            label="Brightness"
            value={opts.brightness}
            min={0.5}
            max={1.5}
            step={0.01}
            display={`${Math.round(opts.brightness * 100)}%`}
            onChange={(v) => set("brightness", v)}
          />
          <Slider
            label="Contrast"
            value={opts.contrast}
            min={0.5}
            max={1.5}
            step={0.01}
            display={`${Math.round(opts.contrast * 100)}%`}
            onChange={(v) => set("contrast", v)}
          />
          <Slider
            label="Saturation"
            value={opts.saturation}
            min={0}
            max={2}
            step={0.01}
            display={`${Math.round(opts.saturation * 100)}%`}
            onChange={(v) => set("saturation", v)}
          />
        </fieldset>

        <div>
          <label htmlFor="format" className="text-sm font-semibold text-slate-900">
            Download format
          </label>
          <select
            id="format"
            value={opts.output_format}
            onChange={(e) => set("output_format", e.target.value as OutputFormat)}
            className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
          >
            <option value="png">PNG (sharpest)</option>
            <option value="jpeg">JPG (smaller file)</option>
          </select>
        </div>
      </aside>
    </div>
  );
}

function ErrorBanner({ message }: { message: ReactNode }) {
  return (
    <p
      role="alert"
      className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      {message}
    </p>
  );
}
