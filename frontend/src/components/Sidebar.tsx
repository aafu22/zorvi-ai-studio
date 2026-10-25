"use client";

import { LogIn, LogOut, Sparkles, UserPlus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/lib/auth";
import { NAV_ITEMS } from "@/lib/nav";

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const { user, loading, logout } = useAuth();

  return (
    <div className="flex h-full flex-col bg-navy-900 text-slate-200">
      <div className="flex items-center gap-2 px-6 py-6">
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
          <Sparkles className="h-5 w-5" aria-hidden="true" />
        </span>
        <span className="text-lg font-semibold tracking-tight text-white">
          Zorvi <span className="text-brand-100">AI</span>
        </span>
      </div>

      <nav aria-label="Main navigation" className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                active
                  ? "bg-navy-700 text-white"
                  : "text-slate-300 hover:bg-navy-800 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-navy-700 px-3 py-4">
        {loading ? null : user ? (
          <div className="space-y-2">
            <div className="px-3">
              <p className="truncate text-sm font-medium text-white">{user.name}</p>
              <p className="truncate text-xs text-slate-400">{user.email}</p>
            </div>
            <button
              onClick={() => {
                onNavigate?.();
                void logout();
              }}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 transition-colors hover:bg-navy-800 hover:text-white"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Sign out
            </button>
          </div>
        ) : (
          <div className="space-y-1">
            <Link
              href="/login"
              onClick={onNavigate}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-300 transition-colors hover:bg-navy-800 hover:text-white"
            >
              <LogIn className="h-4 w-4" aria-hidden="true" />
              Sign in
            </Link>
            <Link
              href="/signup"
              onClick={onNavigate}
              className="flex items-center gap-3 rounded-lg bg-brand-600 px-3 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700"
            >
              <UserPlus className="h-4 w-4" aria-hidden="true" />
              Create account
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
