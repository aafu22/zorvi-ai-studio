"use client";

import { Download, Loader2, RotateCcw, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Slider } from "@/components/Slider";
import { getGraphicOptions, renderGraphic } from "@/lib/api";
import { useCreateFlow } from "@/lib/create-flow";
import {
  brandPatch,
  buildGraphicDefaults,
  contrastRatio,
  STYLE_PALETTES,
  textFromDetails,
} from "@/lib/graphic-defaults";
import type {
  Fit,
  GraphicColors,
  GraphicDraft,
  GraphicFont,
  GraphicOptions,
  GraphicSize,
  GraphicTemplateId,
  OutputFormat,
  PhotoSettings,
} from "@/types/api";

const inputClass =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400";

export function GraphicStudio() {
  const { image, details, style, opts, graphic, setGraphic, brand, pendingText, clearPendingText } = useCreateFlow();
  const [options, setOptions] = useState<GraphicOptions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [rendering, setRendering] = useState(false);
  const [downloading, setDownloading] = useState(false);

  // First visit: build a starting design from the product details and style.
  useEffect(() => {
    if (!graphic) setGraphic(buildGraphicDefaults(details, style, opts, brand));
  }, [graphic, details, style, opts, brand, setGraphic]);

  // Text sent from AI Marketing Brain replaces only headline, subheadline and button text.
  useEffect(() => {
    if (!graphic || !pendingText) return;
    setGraphic({
      ...graphic,
      headline: pendingText.headline.slice(0, 60),
      subheadline: pendingText.subheadline.slice(0, 120),
      cta: pendingText.cta.slice(0, 30),
    });
    clearPendingText();
  }, [graphic, pendingText, setGraphic, clearPendingText]);

  useEffect(() => {
    getGraphicOptions()
      .then(setOptions)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load templates."));
  }, []);

  // Live preview: re-render shortly after any change.
  useEffect(() => {
    if (!graphic || !image) return;
    const controller = new AbortController();
    setRendering(true);
    const timer = setTimeout(async () => {
      try {
        const blob = await renderGraphic({ image_id: image.id, ...graphic }, true, controller.signal);
        const url = URL.createObjectURL(blob);
        setPreviewUrl((old) => {
          if (old) URL.revokeObjectURL(old);
          return url;
        });
        setError(null);
        setRendering(false);
      } catch (e) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Could not render the graphic.");
        setRendering(false);
      }
    }, 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [graphic, image]);

  useEffect(
    () => () => {
      setPreviewUrl((old) => {
        if (old) URL.revokeObjectURL(old);
        return null;
      });
    },
    [],
  );

  const sizeInfo = useMemo(
    () => options?.sizes.find((s) => s.id === graphic?.size),
    [options, graphic?.size],
  );
  const template = useMemo(
    () => options?.templates.find((t) => t.id === graphic?.template),
    [options, graphic?.template],
  );

  if (!graphic || !image) {
    return <div className="h-96 animate-pulse rounded-2xl bg-slate-200" aria-busy="true" />;
  }

  const update = (patch: Partial<GraphicDraft>) => setGraphic((g) => (g ? { ...g, ...patch } : g));
  const updateColors = (patch: Partial<GraphicColors>) =>
    setGraphic((g) => (g ? { ...g, colors: { ...g.colors, ...patch } } : g));
  const updatePhoto = (patch: Partial<PhotoSettings>) =>
    setGraphic((g) => (g ? { ...g, photo: { ...g.photo, ...patch } } : g));

  const ratio = sizeInfo ? sizeInfo.width / sizeInfo.height : 1;
  const lowContrast = contrastRatio(graphic.colors.text, graphic.colors.background) < 4.5;
  const ext = graphic.output_format === "jpeg" ? "jpg" : "png";

  const download = async () => {
    setDownloading(true);
    setError(null);
    try {
      const blob = await renderGraphic({ image_id: image.id, ...graphic }, false);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `zorvi-${graphic.template}-${graphic.size}.${ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed.");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      {/* ------------------------------------------------------------ preview */}
      <div className="space-y-4 lg:sticky lg:top-6 lg:self-start">
        <div className="flex justify-center rounded-2xl border border-slate-200 bg-slate-100 p-4 shadow-card">
          <div
            className="relative overflow-hidden rounded-lg bg-white shadow"
            style={{ aspectRatio: String(ratio), width: `min(100%, ${(68 * ratio).toFixed(2)}vh)` }}
          >
            {previewUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={previewUrl}
                alt={`Preview of your ${sizeInfo?.label ?? "social"} graphic`}
                className="h-full w-full object-contain"
              />
            ) : (
              <div className="h-full w-full animate-pulse bg-slate-200" aria-hidden="true" />
            )}
            {rendering && (
              <span
                role="status"
                className="absolute right-2 top-2 flex items-center gap-1.5 rounded-full bg-white/90 px-2.5 py-1 text-xs font-medium text-slate-700 shadow"
              >
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                Updating
              </span>
            )}
          </div>
        </div>

        {error && (
          <p role="alert" className="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            {error}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void download()}
            disabled={downloading}
            className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {downloading ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Download className="h-4 w-4" aria-hidden="true" />
            )}
            Download {sizeInfo ? `${sizeInfo.width} × ${sizeInfo.height}` : "graphic"} {ext.toUpperCase()}
          </button>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            Format
            <select
              value={graphic.output_format}
              onChange={(e) => update({ output_format: e.target.value as OutputFormat })}
              className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
            >
              <option value="png">PNG</option>
              <option value="jpeg">JPG</option>
            </select>
          </label>
        </div>
        {sizeInfo?.note && <p className="text-xs text-slate-500">{sizeInfo.note}</p>}
      </div>

      {/* ----------------------------------------------------------- controls */}
      <aside className="space-y-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        {!options ? (
          <div className="h-40 animate-pulse rounded-xl bg-slate-200" aria-busy="true" />
        ) : (
          <>
            <Choice
              legend="Template"
              name="template"
              columns={2}
              value={graphic.template}
              items={options.templates.map((t) => ({ value: t.id, label: t.label, hint: t.description }))}
              onChange={(v) => update({ template: v as GraphicTemplateId })}
            />
            <Choice
              legend="Size"
              name="size"
              columns={3}
              value={graphic.size}
              items={options.sizes.map((s) => ({
                value: s.id,
                label: s.label.replace(" post", ""),
                hint: `${s.width}×${s.height}`,
              }))}
              onChange={(v) => update({ size: v as GraphicSize })}
            />

            <fieldset className="space-y-3">
              <div className="flex items-center justify-between">
                <legend className="text-sm font-semibold text-slate-900">Text</legend>
                <button
                  type="button"
                  onClick={() => update(textFromDetails(details))}
                  className="inline-flex items-center gap-1 text-xs font-medium text-brand-600"
                >
                  <RotateCcw className="h-3 w-3" aria-hidden="true" />
                  Reset from details
                </button>
              </div>
              <TextField id="g-headline" label="Headline" max={60} value={graphic.headline} onChange={(v) => update({ headline: v })} />
              <TextField id="g-sub" label="Subheadline" max={120} value={graphic.subheadline} onChange={(v) => update({ subheadline: v })} />
              <TextField id="g-cta" label="Button text" max={30} value={graphic.cta} onChange={(v) => update({ cta: v })} />
              {template?.uses_badge && (
                <TextField id="g-badge" label="Badge (e.g. 20% off)" max={14} value={graphic.badge} onChange={(v) => update({ badge: v })} />
              )}
              <TextField id="g-brand" label="Brand name" max={40} value={graphic.brand_name} onChange={(v) => update({ brand_name: v })} />
              {brand?.has_logo && (
                <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={graphic.show_logo}
                    onChange={(e) => update({ show_logo: e.target.checked })}
                    className="h-4 w-4 accent-brand-600"
                  />
                  Show my logo
                </label>
              )}
              <p className="text-xs text-slate-500">
                Emoji can&apos;t be drawn in graphics, so they are left out. Leave a box empty to hide that element.
              </p>
            </fieldset>

            <fieldset className="space-y-3">
              <div className="flex items-center justify-between">
                <legend className="text-sm font-semibold text-slate-900">Colours</legend>
                <button
                  type="button"
                  onClick={() => updateColors(STYLE_PALETTES[style])}
                  className="inline-flex items-center gap-1 text-xs font-medium text-brand-600"
                >
                  <RotateCcw className="h-3 w-3" aria-hidden="true" />
                  Use {style} palette
                </button>
              </div>
              {brand?.configured && (
                <button
                  type="button"
                  onClick={() => update(brandPatch(brand))}
                  className="inline-flex items-center gap-1 text-xs font-medium text-brand-600"
                >
                  <RotateCcw className="h-3 w-3" aria-hidden="true" />
                  Use my Brand Kit (colours, font{brand.has_logo ? ", logo" : ""})
                </button>
              )}
              <div className="grid grid-cols-3 gap-3">
                <ColorField id="c-bg" label="Background" value={graphic.colors.background} onChange={(v) => updateColors({ background: v })} />
                <ColorField id="c-text" label="Text" value={graphic.colors.text} onChange={(v) => updateColors({ text: v })} />
                <ColorField id="c-accent" label="Accent" value={graphic.colors.accent} onChange={(v) => updateColors({ accent: v })} />
              </div>
              {lowContrast && (
                <p role="status" className="flex items-start gap-1.5 rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  Text and background colours are too similar to read easily. Try a lighter or darker text colour.
                </p>
              )}
            </fieldset>

            <div>
              <label htmlFor="g-font" className="text-sm font-semibold text-slate-900">
                Font
              </label>
              <select
                id="g-font"
                value={graphic.font}
                onChange={(e) => update({ font: e.target.value as GraphicFont })}
                className={inputClass}
              >
                {options.fonts.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.label}
                  </option>
                ))}
              </select>
            </div>

            <fieldset className="space-y-3">
              <legend className="text-sm font-semibold text-slate-900">Photo</legend>
              <Choice
                legend="Photo framing"
                hideLegend
                name="photo-fit"
                columns={2}
                value={graphic.photo.fit}
                items={[
                  { value: "cover", label: "Fill & crop", hint: "" },
                  { value: "contain", label: "Fit whole photo", hint: "" },
                ]}
                onChange={(v) => updatePhoto({ fit: v as Fit })}
              />
              {graphic.photo.fit === "cover" ? (
                <>
                  <Slider label="Zoom" value={graphic.photo.zoom} min={1} max={4} step={0.05} display={`${graphic.photo.zoom.toFixed(2)}×`} onChange={(v) => updatePhoto({ zoom: v })} />
                  <Slider label="Move left / right" value={graphic.photo.focus_x} min={0} max={1} step={0.01} display={`${Math.round(graphic.photo.focus_x * 100)}%`} onChange={(v) => updatePhoto({ focus_x: v })} />
                  <Slider label="Move up / down" value={graphic.photo.focus_y} min={0} max={1} step={0.01} display={`${Math.round(graphic.photo.focus_y * 100)}%`} onChange={(v) => updatePhoto({ focus_y: v })} />
                </>
              ) : (
                <ColorField id="c-photo-bg" label="Photo background" value={graphic.photo.background} onChange={(v) => updatePhoto({ background: v })} />
              )}
            </fieldset>
          </>
        )}
      </aside>
    </div>
  );
}

function TextField({
  id,
  label,
  max,
  value,
  onChange,
}: {
  id: string;
  label: string;
  max: number;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="flex justify-between text-xs font-medium text-slate-700">
        {label}
        <span className="font-normal tabular-nums text-slate-400">
          {value.length}/{max}
        </span>
      </label>
      <input id={id} value={value} maxLength={max} onChange={(e) => onChange(e.target.value)} className={inputClass} />
    </div>
  );
}

function ColorField({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-slate-700">
        {label}
      </label>
      <input
        id={id}
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 h-9 w-full cursor-pointer rounded border border-slate-200 bg-white p-0.5"
      />
    </div>
  );
}

function Choice({
  legend,
  hideLegend,
  name,
  columns,
  value,
  items,
  onChange,
}: {
  legend: string;
  hideLegend?: boolean;
  name: string;
  columns: 2 | 3;
  value: string;
  items: { value: string; label: string; hint: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <fieldset>
      <legend className={hideLegend ? "sr-only" : "text-sm font-semibold text-slate-900"}>{legend}</legend>
      <div className={`mt-2 grid gap-2 ${columns === 3 ? "grid-cols-3" : "grid-cols-2"}`}>
        {items.map((item) => (
          <label
            key={item.value}
            className={`cursor-pointer rounded-lg border px-3 py-2 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500 ${
              value === item.value
                ? "border-brand-500 bg-brand-50 text-brand-700"
                : "border-slate-200 text-slate-700 hover:bg-slate-50"
            }`}
          >
            <input
              type="radio"
              name={name}
              className="sr-only"
              checked={value === item.value}
              onChange={() => onChange(item.value)}
            />
            <span className="block font-medium">{item.label}</span>
            {item.hint && <span className="block text-xs text-slate-500">{item.hint}</span>}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
