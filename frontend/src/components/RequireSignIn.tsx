"use client";

import { Lock } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useAuth } from "@/lib/auth";

/** Link target for the sign-in and sign-up pages that returns the person to the page they came from. */
export function useAuthLinks(): { login: string; signup: string } {
  const pathname = usePathname();
  const next = pathname && pathname !== "/" ? `?next=${encodeURIComponent(pathname)}` : "";
  return { login: `/login${next}`, signup: `/signup${next}` };
}

const buttonPrimary =
  "rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700";
const buttonSecondary =
  "rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50";

/** The "please sign in" card, for places that cannot work without an account. */
export function SignInPrompt({
  feature,
  reason,
  headingTag: Heading = "h1",
}: {
  feature: string;
  reason: string;
  /** Use "h2" when the page already has its own h1. */
  headingTag?: "h1" | "h2";
}) {
  const links = useAuthLinks();
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">
        <Lock className="h-6 w-6" aria-hidden="true" />
      </span>
      <Heading className="mt-4 text-base font-semibold text-slate-900">Sign in to use {feature}</Heading>
      <p className="mt-1 max-w-md text-sm text-slate-500">{reason}</p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link href={links.login} className={buttonPrimary}>
          Sign in
        </Link>
        <Link href={links.signup} className={buttonSecondary}>
          Create account
        </Link>
      </div>
    </div>
  );
}

/** Shows its children only to a signed-in user; everyone else sees the sign-in card. */
export function RequireSignIn({
  feature,
  reason,
  children,
}: {
  feature: string;
  reason: string;
  children: ReactNode;
}) {
  const { user, loading } = useAuth();
  if (loading) return <div className="h-64 animate-pulse rounded-2xl bg-slate-200" aria-busy="true" />;
  if (!user) return <SignInPrompt feature={feature} reason={reason} />;
  return <>{children}</>;
}
