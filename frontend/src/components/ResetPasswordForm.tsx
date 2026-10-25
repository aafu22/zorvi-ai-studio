"use client";

import { CheckCircle2, Loader2 } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { AuthCard } from "@/components/AuthCard";
import { authButtonClass, authInputClass } from "@/components/AuthForm";
import { apiResetPassword } from "@/lib/api";

export function ResetPasswordForm() {
  const token = useSearchParams().get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await apiResetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <AuthCard
        title="Reset link is incomplete"
        footer={
          <Link href="/forgot-password" className="font-semibold text-brand-600 hover:text-brand-700">
            Request a new link
          </Link>
        }
      >
        <p className="text-sm text-slate-600">
          This page needs the link from your email. Open the full link, or request a new one.
        </p>
      </AuthCard>
    );
  }

  if (done) {
    return (
      <AuthCard title="Password changed">
        <div role="status" className="flex items-start gap-3 rounded-lg bg-green-50 p-4 text-sm text-slate-700">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-green-600" aria-hidden="true" />
          <p>Your password has been updated and you were signed out everywhere. Sign in with the new one.</p>
        </div>
        <Link href="/login" className={`${authButtonClass} mt-4`}>
          Go to sign in
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password" subtitle="Use at least 8 characters.">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="password" className="text-sm font-medium text-slate-700">
            New password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={authInputClass}
          />
        </div>
        <div>
          <label htmlFor="confirm" className="text-sm font-medium text-slate-700">
            Confirm new password
          </label>
          <input
            id="confirm"
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            className={authInputClass}
          />
        </div>
        {error && (
          <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            <p>{error}</p>
            <Link href="/forgot-password" className="mt-1 inline-block font-semibold underline">
              Request a new link
            </Link>
          </div>
        )}
        <button type="submit" disabled={busy || !password || !confirm} className={authButtonClass}>
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          Change password
        </button>
      </form>
    </AuthCard>
  );
}
