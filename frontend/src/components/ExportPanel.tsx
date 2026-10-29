"use client";

import { Archive, Check, FolderPlus, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useAuthLinks } from "@/components/RequireSignIn";
import { exportKit, saveToHistory } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCreateFlow } from "@/lib/create-flow";
import { saveBlob, slugify } from "@/lib/download";
import type { GraphicSize } from "@/types/api";

const SIZES: { value: GraphicSize; label: string }[] = [
  { value: "square", label: "Square 1080×1080" },
  { value: "portrait", label: "Portrait 1080×1350" },
  { value: "story", label: "Story 1080×1920" },
];

type Msg = { kind: "ok" | "error"; text: string } | null;

/** Step 5 actions: download the whole marketing kit as a ZIP, or save the project to history. */
export function ExportPanel() {
  const { user } = useAuth();
  const authLinks = useAuthLinks();
  const { image, opts, details, style, copy, graphic } = useCreateFlow();
  const [sizes, setSizes] = useState<GraphicSize[]>(["square"]);
  const [includeJson, setIncludeJson] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exportMsg, setExportMsg] = useState<Msg>(null);
  const [saveMsg, setSaveMsg] = useState<Msg>(null);
  const [name, setName] = useState(details.product_name);

  if (!image || !copy || !graphic) return null;

  const toggle = (s: GraphicSize) =>
    setSizes((cur) => (cur.includes(s) ? cur.filter((x) => x !== s) : [...cur, s]));

  const download = async () => {
    setExporting(true);
    setExportMsg(null);
    try {
      const blob = await exportKit({
        image_id: image.id,
        details: { ...details, style },
        copy,
        edit: opts,
        graphic,
        sizes,
        include_json: includeJson,
      });
      saveBlob(blob, `zorvi-${slugify(details.product_name)}-kit.zip`);
      setExportMsg({ kind: "ok", text: "Kit downloaded." });
    } catch (e) {
      setExportMsg({ kind: "error", text: e instanceof Error ? e.message : "Export failed." });
    } finally {
      setExporting(false);
    }
  };

  const save = async () => {
    setSaving(true);
    setSaveMsg(null);
    try {
      await saveToHistory({
        image_id: image.id,
        name: name.trim() || details.product_name,
        product_name: details.product_name,
        state: { step: 5, opts, details, style, copy, graphic },
      });
      setSaveMsg({ kind: "ok", text: "Saved. Find it under Content History." });
    } catch (e) {
      setSaveMsg({ kind: "error", text: e instanceof Error ? e.message : "Could not save." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <h3 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          <Archive className="h-4 w-4 text-brand-600" aria-hidden="true" />
          Marketing kit (.zip)
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          Edited image, your graphic in the sizes you pick, all text as Markdown and a plain product
          description.
        </p>
        <fieldset className="mt-3">
          <legend className="text-xs font-semibold text-slate-700">Graphic sizes</legend>
          <div className="mt-1 space-y-1">
            {SIZES.map((s) => (
              <label key={s.value} className="flex cursor-pointer items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={sizes.includes(s.value)}
                  onChange={() => toggle(s.value)}
                  className="h-4 w-4 accent-brand-600"
                />
                {s.label}
              </label>
            ))}
          </div>
        </fieldset>
        <label className="mt-3 flex cursor-pointer items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={includeJson}
            onChange={(e) => setIncludeJson(e.target.checked)}
            className="h-4 w-4 accent-brand-600"
          />
          Include campaign.json (settings and text)
        </label>
        <button
          type="button"
          onClick={() => void download()}
          disabled={exporting || sizes.length === 0}
          className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {exporting && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          {exporting ? "Building kit…" : "Download marketing kit"}
        </button>
        {sizes.length === 0 && <p className="mt-2 text-xs text-slate-500">Choose at least one size.</p>}
        <Message msg={exportMsg} />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <h3 className="flex items-center gap-2 text-base font-semibold text-slate-900">
          <FolderPlus className="h-4 w-4 text-brand-600" aria-hidden="true" />
          Save to history
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          Keeps this project (photo, settings and text) in your account so you can reopen it later.
        </p>
        {!user && (
          <p className="mt-2 text-xs text-slate-600">
            <Link href={authLinks.login} className="font-semibold text-brand-700 underline">Sign in</Link> or{" "}
            <Link href={authLinks.signup} className="font-semibold text-brand-700 underline">create an account</Link>{" "}
            to save projects. Downloading the kit works without one.
          </p>
        )}
        <label htmlFor="save-name" className="mt-3 block text-xs font-semibold text-slate-700">
          Project name
        </label>
        <input
          id="save-name"
          maxLength={80}
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900"
        />
        <button
          type="button"
          onClick={() => void save()}
          disabled={saving || !name.trim() || !user}
          className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          Save project
        </button>
        <Message msg={saveMsg} />
      </div>
    </div>
  );
}

function Message({ msg }: { msg: Msg }) {
  if (!msg) return null;
  return (
    <p
      role={msg.kind === "error" ? "alert" : "status"}
      className={`mt-3 flex items-center gap-1.5 text-sm ${msg.kind === "error" ? "text-red-700" : "text-emerald-700"}`}
    >
      {msg.kind === "ok" && <Check className="h-4 w-4" aria-hidden="true" />}
      {msg.text}
    </p>
  );
}
