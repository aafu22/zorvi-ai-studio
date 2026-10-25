"use client";

import { Loader2, MailCheck } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { AuthCard } from "@/components/AuthCard";
import { authButtonClass, authInputClass } from "@/components/AuthForm";
import { apiForgotPassword } from "@/lib/api";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setDone((await apiForgotPassword(email.trim())).message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard
      title="Forgot your password?"
      subtitle="Enter your email and we'll send you a link to choose a new one."
      footer={
        <Link href="/login" className="font-semibold text-brand-600 hover:text-brand-700">
          Back to sign in
        </Link>
      }
    >
      {done ? (
        <div role="status" className="flex items-start gap-3 rounded-lg bg-brand-50 p-4 text-sm text-slate-700">
          <MailCheck className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
          <p>{done} The link works for a limited time and can be used once.</p>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="email" className="text-sm font-medium text-slate-700">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={authInputClass}
              placeholder="you@example.com"
            />
          </div>
          {error && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </p>
          )}
          <button type="submit" disabled={busy || !email.trim()} className={authButtonClass}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Send reset link
          </button>
        </form>
      )}
    </AuthCard>
  );
}
