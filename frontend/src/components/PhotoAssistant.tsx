"use client";

import { useEffect, useState } from "react";
import { AlertCircle, CheckCircle2, ImagePlus, Loader2, Sparkles, Upload, X } from "lucide-react";
import { analyzePhoto } from "@/lib/api";
import Link from "next/link";
import { createProductId, getProduct, PRODUCT_HANDOFF_KEY, saveProduct, type SavedProduct } from "@/lib/product-library";

type PhotoAnalysis = {
  product_type: string;
  visible_features: string[];
  product_title: string;
  visual_description: string;
  background_suggestions: string[];
  composition_suggestions: string[];
  lighting_recommendations: string[];
  framing_recommendations: string[];
  color_palette: string[];
  confidence_note: string;
};

const groups: { key: keyof Pick<PhotoAnalysis, "visible_features" | "background_suggestions" | "composition_suggestions" | "lighting_recommendations" | "framing_recommendations" | "color_palette">; title: string }[] = [
  { key: "visible_features", title: "Visible features" },
  { key: "background_suggestions", title: "Background ideas" },
  { key: "composition_suggestions", title: "Composition" },
  { key: "lighting_recommendations", title: "Lighting" },
  { key: "framing_recommendations", title: "Framing" },
  { key: "color_palette", title: "Suggested colour palette" },
];

export function PhotoAssistant() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState<PhotoAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [savedId, setSavedId] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    const id = sessionStorage.getItem("zorvi.photo-assistant.current");
    if (!id) return;
    getProduct(id).then((saved) => {
      if (!saved) return;
      setSavedId(saved.id);
      setFile(new File([saved.image], saved.name, { type: saved.imageType || saved.image.type || "image/jpeg" }));
      setResult(saved.analysis);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!file) { setPreview(""); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const chooseFile = (next: File | undefined) => {
    setResult(null);
    setError("");
    setSaveMessage("");
    if (!next) return;
    if (! ["image/jpeg", "image/png", "image/webp"].includes(next.type)) {
      setFile(null);
      setError("Please choose a JPG, PNG, or WebP image.");
      return;
    }
    if (next.size > 10 * 1024 * 1024) {
      setFile(null);
      setError("Please choose an image smaller than 10 MB.");
      return;
    }
    const id = createProductId();
    setSavedId(id);
    sessionStorage.setItem("zorvi.photo-assistant.current", id);
    setFile(next);
    void saveProduct({ id, name: next.name, createdAt: new Date().toISOString(), image: next, imageType: next.type, analysis: null })
      .then(() => setSaveMessage("Photo saved to your product library."))
      .catch(() => setSaveMessage("Could not save this photo in browser storage. Check available storage."));
  };

  const analyze = async () => {
    if (!file) { setError("Upload a product photo first."); return; }
    setBusy(true); setError(""); setResult(null);
    try {
      const analysis = await analyzePhoto<PhotoAnalysis>(file);
      setResult(analysis);
      if (savedId && file) {
        await saveProduct({ id: savedId, name: file.name, createdAt: new Date().toISOString(), image: file, imageType: file.type, analysis });
        setSaveMessage("Photo and AI analysis saved to your product library.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not analyse this photo. Please try again.");
    } finally { setBusy(false); }
  };

  const copyText = async (value: string) => {
    try { await navigator.clipboard.writeText(value); } catch { setError("Clipboard access failed. You can select and copy the text manually."); }
  };

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-5 py-8 sm:px-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700"><Sparkles className="h-3.5 w-3.5" /> REAL AI · IMAGE UNDERSTANDING</div>
          <h1 className="text-3xl font-bold tracking-tight">AI Product Photo Assistant</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Upload a product photo to identify visible details and get practical ideas for backgrounds, composition, lighting, framing, and colours.</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-semibold">1. Upload your product photo</h2>
          <label className="flex min-h-64 cursor-pointer flex-col items-center justify-center overflow-hidden rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-4 text-center transition hover:border-brand-400 hover:bg-brand-50/40">
            {preview ? <img src={preview} alt="Product photo preview" className="max-h-72 w-full rounded-lg object-contain" /> : <><ImagePlus className="mb-3 h-10 w-10 text-slate-400" /><span className="font-medium">Choose a product image</span><span className="mt-1 text-xs text-slate-500">JPG, PNG or WebP · Up to 10 MB</span></>}
            <input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(e) => chooseFile(e.target.files?.[0])} />
          </label>
          {file && <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm"><span className="truncate">{file.name}</span><button type="button" onClick={() => { setFile(null); setResult(null); setSavedId(""); sessionStorage.removeItem("zorvi.photo-assistant.current"); setError(""); }} className="rounded p-1 text-slate-500 hover:bg-slate-200" aria-label="Remove image"><X className="h-4 w-4" /></button></div>}
          <button type="button" onClick={analyze} disabled={!file || busy} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-3 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}{busy ? "Analysing photo…" : "Analyse with AI"}
          </button>
          <p className="text-xs leading-5 text-slate-500">Your image is sent to the configured Gemini model for analysis. Avoid uploading confidential images. This feature requires a valid backend Gemini API key.</p>
          {saveMessage && <p role="status" className="text-xs text-emerald-700">{saveMessage}</p>}
          {error && <div role="alert" className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{error}</span></div>}
        </section>

        <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          {!result && !busy && <div className="flex min-h-80 flex-col items-center justify-center text-center"><div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-50 text-brand-600"><Upload className="h-7 w-7" /></div><h2 className="font-semibold">Your photo insights will appear here</h2><p className="mt-2 max-w-sm text-sm leading-6 text-slate-500">The AI will analyse visible product details and suggest how to present the product more effectively.</p></div>}
          {busy && <div className="flex min-h-80 flex-col items-center justify-center text-center"><Loader2 className="mb-4 h-9 w-9 animate-spin text-brand-600" /><h2 className="font-semibold">Looking at your product photo</h2><p className="mt-2 text-sm text-slate-500">This can take a few seconds.</p></div>}
          {result && <div className="space-y-5">
            <div className="flex items-start justify-between gap-3"><div><div className="mb-1 flex items-center gap-2 text-xs font-semibold text-emerald-700"><CheckCircle2 className="h-4 w-4" /> ANALYSIS COMPLETE</div><h2 className="text-xl font-bold">{result.product_title}</h2><p className="mt-1 text-sm text-slate-500">Likely product type: {result.product_type}</p></div><button type="button" onClick={() => copyText(`${result.product_title}\n\n${result.visual_description}\n\n${groups.map(g => `${g.title}:\n${result[g.key].map(x => `• ${x}`).join("\n")}`).join("\n\n")}`)} className="shrink-0 rounded-lg border border-slate-200 px-3 py-2 text-xs font-medium hover:bg-slate-50">Copy report</button></div>
            <div className="rounded-xl bg-slate-50 p-4"><h3 className="text-sm font-semibold">Visual description</h3><p className="mt-2 text-sm leading-6 text-slate-700">{result.visual_description}</p><button type="button" onClick={() => copyText(result.product_title)} className="mt-3 text-xs font-semibold text-brand-700 hover:underline">Copy product title</button></div>
            <div className="grid gap-4 sm:grid-cols-2">{groups.map((group) => <div key={group.key} className="rounded-xl border border-slate-200 p-4"><h3 className="font-semibold">{group.title}</h3><ul className="mt-2 space-y-2 text-sm leading-5 text-slate-600">{result[group.key].map((item, i) => <li key={`${group.key}-${i}`} className="flex gap-2"><span className="text-brand-600">•</span><span>{item}</span></li>)}</ul></div>)}</div>
            <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900"><strong>Review before using:</strong> {result.confidence_note} AI may misidentify objects or infer details not visible in an image. Verify the suggestions before publishing.</p>
            <div className="flex flex-wrap gap-3 border-t border-slate-200 pt-4">
              <button type="button" onClick={() => { if (!savedId) return; sessionStorage.setItem(PRODUCT_HANDOFF_KEY, savedId); window.location.href = "/create"; }} className="rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700">Use in Create Content</button>
              <Link href="/assets" className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">View My Assets</Link>
              <button type="button" onClick={() => { setFile(null); setPreview(""); setResult(null); setSavedId(""); sessionStorage.removeItem("zorvi.photo-assistant.current"); setError(""); setSaveMessage(""); }} className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50">Analyse another photo</button>
            </div>
          </div>}
        </section>
      </div>
    </main>
  );
}
