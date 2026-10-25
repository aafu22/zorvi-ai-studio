"use client";

import { Loader2, Sparkles } from "lucide-react";
import { useState, type ReactNode } from "react";

import { startDemo } from "@/lib/api";
import type { DemoResponse } from "@/types/api";

/**
 * Loads the built-in sample product (a demo candle photo drawn by a script in sample_assets/,
 * with example details). Works without any upload, so a visitor can try the whole app in seconds.
 */
export function DemoButton({
  onLoaded,
  className,
  errorClassName = "text-red-700",
  children,
}: {
  onLoaded: (demo: DemoResponse) => void;
  className?: string;
  errorClassName?: string;
  children?: ReactNode;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      onLoaded(await startDemo());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start the demo.");
      setLoading(false);
    }
  };

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={() => void run()}
        disabled={loading}
        className={
          className ??
          "inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
        }
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <Sparkles className="h-4 w-4" aria-hidden="true" />
        )}
        {children ?? "Try the demo"}
      </button>
      {error && (
        <span role="alert" className={`text-xs ${errorClassName}`}>
          {error}
        </span>
      )}
    </span>
  );
}
