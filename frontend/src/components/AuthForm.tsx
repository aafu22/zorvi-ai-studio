"use client";

import { Loader2, MailCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { AuthCard } from "@/components/AuthCard";
import { ApiError, apiResendVerification } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const authInputClass =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400";
export const authButtonClass =
  "flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60";
const linkClass = "font-semibold text-brand-600 hover:text-brand-700";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const isSignup = mode === "signup";
  const router = useRouter();
  const { user, loading, login, signup } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsVerification, setNeedsVerification] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null); // set after sign-up when verification is required
  const [resendNote, setResendNote] = useState<string | null>(null);

  // Already signed in? Go to the dashboard.
  useEffect(() => {
    if (!loading && user) router.replace("/");
  }, [loading, user, router]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setNeedsVerification(false);
    setResendNote(null);
    if (isSignup && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      if (isSignup) {
        const { verificationRequired } = await signup(name.trim(), email.trim(), password);
        if (verificationRequired) {
          setSentTo(email.trim());
          setBusy(false);
          return;
        }
      } else {
        await login(email.trim(), password);
      }
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      // The backend answers 403 only when the password was right but the email is not verified yet.
      setNeedsVerification(err instanceof ApiError && err.status === 403);
      setBusy(false);
    }
  };

  const resend = async (address: string) => {
    setResendNote(null);
    try {
      const res = await apiResendVerification(address);
      setResendNote(res.message);
    } catch (err) {
      setResendNote(err instanceof Error ? err.message : "Could not resend the email.");
    }
  };

  // After sign-up: tell the user to check their inbox.
  if (sentTo) {
    return (
      <AuthCard
        title="Check your email"
        subtitle={`We sent a verification link to ${sentTo}. Click it to activate your account, then sign in.`}
        footer={
          <Link href="/login" className={linkClass}>
            Go to sign in
          </Link>
        }
      >
        <div className="flex items-start gap-3 rounded-lg bg-brand-50 p-4 text-sm text-slate-700">
          <MailCheck className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
          <p>Can&apos;t find it? Check your spam folder, or ask for a new link.</p>
        </div>
        <button
          type="button"
          onClick={() => resend(sentTo)}
          className="mt-4 w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50"
        >
          Resend verification email
        </button>
        {resendNote && (
          <p role="status" className="mt-3 text-center text-sm text-slate-600">
            {resendNote}
          </p>
        )}
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title={isSignup ? "Create your account" : "Welcome back"}
      subtitle={
        isSignup
          ? "Sign up to start creating marketing content."
          : "Sign in to continue to Zorvi AI Studio."
      }
      footer={
        <>
          {isSignup ? "Already have an account?" : "New to Zorvi?"}{" "}
          <Link href={isSignup ? "/login" : "/signup"} className={linkClass}>
            {isSignup ? "Sign in" : "Create an account"}
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {isSignup && (
          <div>
            <label htmlFor="name" className="text-sm font-medium text-slate-700">
              Name
            </label>
            <input
              id="name"
              type="text"
              autoComplete="name"
              required
              maxLength={80}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={authInputClass}
              placeholder="Your name"
            />
          </div>
        )}
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
        <div>
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="text-sm font-medium text-slate-700">
              Password
            </label>
            {!isSignup && (
              <Link href="/forgot-password" className="text-sm text-brand-600 hover:text-brand-700">
                Forgot password?
              </Link>
            )}
          </div>
          <input
            id="password"
            type="password"
            autoComplete={isSignup ? "new-password" : "current-password"}
            required
            minLength={isSignup ? 8 : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={authInputClass}
            placeholder={isSignup ? "At least 8 characters" : "Your password"}
          />
        </div>

        {error && (
          <div role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            <p>{error}</p>
            {needsVerification && (
              <button
                type="button"
                onClick={() => resend(email.trim())}
                className="mt-1 font-semibold underline"
              >
                Resend verification email
              </button>
            )}
          </div>
        )}
        {resendNote && (
          <p role="status" className="text-sm text-slate-600">
            {resendNote}
          </p>
        )}

        <button
          type="submit"
          disabled={busy || !email || !password || (isSignup && !name.trim())}
          className={authButtonClass}
        >
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          {isSignup ? "Create account" : "Sign in"}
        </button>
      </form>
    </AuthCard>
  );
}
