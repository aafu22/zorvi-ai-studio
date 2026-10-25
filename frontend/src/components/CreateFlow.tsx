"use client";

import { ArrowLeft, ArrowRight, RotateCcw } from "lucide-react";

import { CopyStudio } from "@/components/CopyStudio";
import { DetailsForm } from "@/components/DetailsForm";
import { ImageEditor } from "@/components/ImageEditor";
import { ReviewStep } from "@/components/ReviewStep";
import { StylePicker } from "@/components/StylePicker";
import { deleteImage } from "@/lib/api";
import { CreateFlowProvider, useCreateFlow } from "@/lib/create-flow";
import { CREATION_STEPS } from "@/lib/nav";

const STEP_INTRO = [
  "Upload your product photo and prepare it for Instagram.",
  "Tell us about the product. Only the name is required.",
  "Pick the look you want for your content.",
  "Review, edit and copy your marketing text.",
  "Design your social graphic, then download it with your image and text.",
];

export function CreateFlow() {
  return (
    <CreateFlowProvider>
      <FlowInner />
    </CreateFlowProvider>
  );
}

function FlowInner() {
  const { hydrated, step, setStep, image, details, copy, reset, pendingText } = useCreateFlow();

  if (!hydrated) {
    return <div className="h-64 animate-pulse rounded-2xl bg-slate-200" aria-busy="true" />;
  }

  const hasName = details.product_name.trim().length > 0;
  const canVisit = (n: number): boolean => {
    if (n <= 1) return true;
    if (n === 2) return !!image;
    if (n === 3 || n === 4) return !!image && hasName;
    return !!image && hasName && !!copy;
  };

  const blockedReason = (n: number): string => {
    if (!image) return "Upload a photo to continue.";
    if (!hasName) return "Enter a product name to continue.";
    if (n === 5 && !copy) return "Generate your copy to continue.";
    return "";
  };

  const startOver = async () => {
    if (!window.confirm("Start over? This clears your photo, details and text.")) return;
    const id = image?.id;
    reset();
    if (id) {
      try {
        await deleteImage(id);
      } catch {
        /* expires automatically */
      }
    }
  };

  const next = step + 1;
  const nextBlocked = step < 5 && !canVisit(next);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Create Content</h1>
          <p className="mt-1 text-sm text-slate-500">
            Step {step} of 5: {STEP_INTRO[step - 1]}
          </p>
        </div>
        <button
          type="button"
          onClick={() => void startOver()}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
          Start over
        </button>
      </div>

      {pendingText && step !== 5 && (
        <p role="status" className="rounded-xl border border-brand-200 bg-brand-50 px-4 py-3 text-sm text-brand-800">
          Text from AI Marketing Brain is ready. It will fill the graphic&apos;s headline, subheadline and
          button text when you reach step 5. {!image ? "Upload a photo to continue." : ""}
        </p>
      )}

      <nav aria-label="Creation steps">
        <ol className="flex flex-wrap gap-2 text-xs">
          {CREATION_STEPS.map((s, i) => {
            const n = i + 1;
            const active = n === step;
            const allowed = canVisit(n);
            return (
              <li key={s.title}>
                <button
                  type="button"
                  disabled={!allowed}
                  aria-current={active ? "step" : undefined}
                  onClick={() => setStep(n)}
                  className={`rounded-full px-3 py-1.5 font-medium transition-colors ${
                    active
                      ? "bg-brand-600 text-white"
                      : allowed
                        ? "bg-brand-50 text-brand-700 hover:bg-brand-100"
                        : "cursor-not-allowed bg-slate-200 text-slate-500"
                  }`}
                >
                  {n}. {s.title}
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      <div>
        {step === 1 && <ImageEditor />}
        {step === 2 && <DetailsForm />}
        {step === 3 && <StylePicker />}
        {step === 4 && <CopyStudio />}
        {step === 5 && <ReviewStep />}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-5">
        <button
          type="button"
          onClick={() => setStep(step - 1)}
          disabled={step === 1}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:invisible"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Back
        </button>
        {step < 5 && (
          <div className="flex items-center gap-3">
            {nextBlocked && (
              <span id="next-hint" className="text-xs text-slate-500">
                {blockedReason(next)}
              </span>
            )}
            <button
              type="button"
              onClick={() => setStep(next)}
              disabled={nextBlocked}
              aria-describedby={nextBlocked ? "next-hint" : undefined}
              className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {step === 4 ? "Preview & export" : "Next"}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
