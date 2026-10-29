"use client";

import { FolderOpen, Loader2, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AuthedImage } from "@/components/AuthedImage";
import { deleteFromHistory, listHistory, openFromHistory } from "@/lib/api";
import { normalizeSnapshot, writeFlowSnapshot } from "@/lib/create-flow";
import type { CampaignSummary } from "@/types/api";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function HistoryList() {
  const router = useRouter();
  const [items, setItems] = useState<CampaignSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(() => {
    setError(null);
    listHistory()
      .then(setItems)
      .catch((e) => {
        setItems([]);
        setError(e instanceof Error ? e.message : "Could not load your projects.");
      });
  }, []);

  useEffect(load, [load]);

  const open = async (c: CampaignSummary) => {
    setBusyId(c.id);
    setError(null);
    try {
      const { image, state } = await openFromHistory(c.id);
      writeFlowSnapshot({ ...normalizeSnapshot(state), image, step: 5 });
      router.push("/create");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open that project.");
      setBusyId(null);
    }
  };

  const remove = async (c: CampaignSummary) => {
    if (!window.confirm(`Delete "${c.name}"? This cannot be undone.`)) return;
    setBusyId(c.id);
    setError(null);
    try {
      await deleteFromHistory(c.id);
      setItems((list) => (list ?? []).filter((x) => x.id !== c.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete that project.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Content History</h1>
        <p className="mt-1 text-sm text-slate-500">
          Projects you saved are stored in your account and are visible only to you. Open one to keep
          editing or export it again.
        </p>
      </div>

      {error && (
        <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      )}

      {items === null ? (
        <div className="h-48 animate-pulse rounded-2xl bg-slate-200" aria-busy="true" />
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">
            <FolderOpen className="h-6 w-6" aria-hidden="true" />
          </span>
          <h2 className="mt-4 text-base font-semibold text-slate-900">No saved projects yet</h2>
          <p className="mt-1 max-w-md text-sm text-slate-500">
            Finish a project and choose &ldquo;Save to history&rdquo; on the last step. It will appear here.
          </p>
          <Link
            href="/create"
            className="mt-6 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
          >
            Create content
          </Link>
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((c) => (
            <li key={c.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
              <AuthedImage
                path={c.thumbnail_url}
                alt={`Thumbnail of ${c.name}`}
                className="aspect-square w-full bg-slate-100 object-cover"
              />
              <div className="p-4">
                <p className="truncate text-sm font-semibold text-slate-900">{c.name}</p>
                <p className="truncate text-xs text-slate-500">
                  {[c.product_name, formatDate(c.created_at)].filter(Boolean).join(" · ")}
                </p>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={() => void open(c)}
                    disabled={busyId !== null}
                    className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-brand-600 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
                  >
                    {busyId === c.id && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
                    Open
                  </button>
                  <button
                    type="button"
                    onClick={() => void remove(c)}
                    disabled={busyId !== null}
                    aria-label={`Delete ${c.name}`}
                    className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-700 hover:bg-slate-50 disabled:opacity-60"
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
