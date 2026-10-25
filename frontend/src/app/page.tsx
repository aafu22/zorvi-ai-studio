import { DashboardActions } from "@/components/DashboardActions";
import { Stepper } from "@/components/Stepper";

export default function DashboardPage() {
  return (
    <div className="space-y-10">
      <section className="rounded-3xl bg-gradient-to-br from-navy-900 via-navy-800 to-brand-700 p-8 text-white shadow-card sm:p-12">
        <p className="text-sm font-medium text-brand-100">Zorvi AI Studio</p>
        <h1 className="mt-2 max-w-2xl text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
          Turn one product photo into a complete marketing kit.
        </h1>
        <p className="mt-4 max-w-xl text-slate-200">
          Upload a product image, add a few details, and get edited images,
          captions, hashtags and ready-to-post social graphics.
        </p>
        <DashboardActions />
      </section>

      <section aria-labelledby="flow-heading">
        <h2 id="flow-heading" className="mb-4 text-lg font-semibold text-slate-900">
          How it works
        </h2>
        <Stepper />
      </section>
    </div>
  );
}
