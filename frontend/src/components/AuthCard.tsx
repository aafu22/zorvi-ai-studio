import { Sparkles } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

/** Shared full-screen layout for the sign in, sign up, verify and reset pages. */
export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-2">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-white">
            <Sparkles className="h-5 w-5" aria-hidden="true" />
          </span>
          <span className="text-xl font-semibold tracking-tight text-navy-900">
            Zorvi <span className="text-brand-600">AI</span>
          </span>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-card sm:p-8">
          <h1 className="text-xl font-bold text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
          <div className="mt-6">{children}</div>
          {footer && <div className="mt-6 text-center text-sm text-slate-600">{footer}</div>}
        </div>

        <p className="mt-4 text-center text-sm">
          <Link href="/" className="text-slate-500 hover:text-slate-700">
            Continue without signing in
          </Link>
        </p>
      </div>
    </div>
  );
}
