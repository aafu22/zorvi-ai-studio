"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { DemoButton } from "@/components/DemoButton";
import { writeFlowSnapshot } from "@/lib/create-flow";

export function DashboardActions() {
  const router = useRouter();
  return (
    <div className="mt-8 flex flex-wrap items-start gap-3">
      <Link
        href="/create"
        className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-navy-900 hover:bg-brand-50"
      >
        Start creating
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Link>
      <DemoButton
        className="inline-flex items-center gap-2 rounded-xl border border-white/40 px-5 py-3 text-sm font-semibold text-white hover:bg-white/10 disabled:opacity-60"
        errorClassName="text-red-200"
        onLoaded={(demo) => {
          writeFlowSnapshot({ image: demo.image, details: demo.details, style: demo.style, step: 2 });
          router.push("/create");
        }}
      >
        Try the demo
      </DemoButton>
    </div>
  );
}
