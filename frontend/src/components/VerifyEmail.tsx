"use client";

import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { AuthCard } from "@/components/AuthCard";
import { authButtonClass, authInputClass } from "@/components/AuthForm";
import { apiResendVerification, apiVerifyEmail } from "@/lib/api";

type State = { kind: "checking" } | { kind: "ok"; message: string } | { kind: "error"; message: string };

export function VerifyEmail() {
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<State>(
    token ? { kind: "checking" } : { kind: "error", message: "This page needs the link from your email." },
  );
  const started = useRef(false); // the link is single-use, so only ever call the backend once
  const [email, setEmail] = useState("");
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    if (!token || started.current) return;
    started.current = true;
    apiVerifyEmail(token)
      .then((res) => setState({ kind: "ok", message: res.message }))
      .catch((err) =>
        setState({ kind: "error", message: err instanceof Error ? err.message : "Something went wrong." }),
      );
  }, [token]);

  const resend = async () => {
    setNote(null);
    try {
      setNote((await apiResendVerification(email.trim())).message);
    } catch (err) {
      setNote(err instanceof Error ? err.message : "Could not resend the email.");
    }
  };

  return (
    <AuthCard title="Email verification">
      {state.kind === "checking" && (
        <p className="flex items-center gap-2 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Verifying your email...
        </p>
      )}

      {state.kind === "ok" && (
        <>
          <div role="status" className="flex items-start gap-3 rounded-lg bg-green-50 p-4 text-sm text-slate-700">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-600" aria-hidden="true" />
            <p>{state.message}</p>
          </div>
          <Link href="/login" className={`${authButtonClass} mt-4`}>
            Go to sign in
          </Link>
        </>
      )}

      {state.kind === "error" && (
        <>
          <div role="alert" className="flex items-start gap-3 rounded-lg bg-red-50 p-4 text-sm text-red-700">
            <XCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <p>{state.message}</p>
          </div>
          <p className="mt-4 text-sm text-slate-600">Enter your email to get a new verification link.</p>
          <input
            type="email"
            aria-label="Email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={authInputClass}
            placeholder="you@example.com"
          />
          <button
            type="button"
            onClick={resend}
            disabled={!email.trim()}
            className={`${authButtonClass} mt-3`}
          >
            Send a new link
          </button>
          {note && (
            <p role="status" className="mt-3 text-sm text-slate-600">
              {note}
            </p>
          )}
        </>
      )}
    </AuthCard>
  );
}
