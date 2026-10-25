"use client";

import { CheckCircle2, Loader2, RefreshCw, XCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { API_URL, getHealth } from "@/lib/api";
import type { HealthResponse } from "@/types/api";

type State =
  | { kind: "loading" }
  | { kind: "ok"; data: HealthResponse }
  | { kind: "error"; message: string };

export function BackendStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  const check = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      setState({ kind: "ok", data: await getHealth() });
    } catch (e) {
      setState({
        kind: "error",
        message: e instanceof Error ? e.message : "Unknown error",
      });
    }
  }, []);

  useEffect(() => {
    void check();
  }, [check]);

  return (
    <section
      aria-live="polite"
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Backend status</h2>
          <p className="mt-0.5 text-xs text-slate-500">{API_URL}</p>
        </div>
        <button
          onClick={() => void check()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
          Recheck
        </button>
      </div>

      <div className="mt-4 text-sm">
        {state.kind === "loading" && (
          <p className="flex items-center gap-2 text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Checking connection…
          </p>
        )}
        {state.kind === "ok" && (
          <div className="space-y-2">
            <p className="flex items-center gap-2 font-medium text-emerald-700">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              Connected · v{state.data.version} ({state.data.environment})
            </p>
            <ul className="text-xs text-slate-500">
              <li>
                Background removal:{" "}
                {state.data.capabilities.background_removal
                  ? "installed"
                  : "not installed (optional)"}
              </li>
              <li>
                LLM provider:{" "}
                {state.data.capabilities.llm_provider
                  ? "configured"
                  : "not configured (template-based copy will be used)"}
              </li>
            </ul>
          </div>
        )}
        {state.kind === "error" && (
          <p className="flex items-start gap-2 text-red-700">
            <XCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            {state.message}
          </p>
        )}
      </div>
    </section>
  );
}
