import { CREATION_STEPS } from "@/lib/nav";

export function Stepper() {
  return (
    <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {CREATION_STEPS.map((step, i) => (
        <li
          key={step.title}
          className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-50 text-sm font-semibold text-brand-700">
            {i + 1}
          </span>
          <h3 className="mt-3 text-sm font-semibold text-slate-900">{step.title}</h3>
          <p className="mt-1 text-sm text-slate-500">{step.description}</p>
        </li>
      ))}
    </ol>
  );
}
