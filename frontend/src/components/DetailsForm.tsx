"use client";

import { useCreateFlow } from "@/lib/create-flow";
import type { ProductDetails, Tone } from "@/types/api";

const CATEGORIES = [
  "Fashion & clothing",
  "Jewellery & accessories",
  "Beauty & skincare",
  "Home & decor",
  "Food & bakery",
  "Candles & fragrance",
  "Bags & footwear",
  "Gifts & stationery",
  "Other",
];

export const TONES: { value: Tone; label: string; hint: string }[] = [
  { value: "friendly", label: "Friendly", hint: "Warm and chatty" },
  { value: "professional", label: "Professional", hint: "Clear and polished" },
  { value: "luxury", label: "Luxury", hint: "Elegant and refined" },
  { value: "playful", label: "Playful", hint: "Fun and energetic" },
  { value: "festive", label: "Festive", hint: "Celebratory" },
];

const inputClass =
  "mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400";

export function DetailsForm() {
  const { details, setDetails } = useCreateFlow();
  const set = <K extends keyof ProductDetails>(key: K, value: ProductDetails[K]) =>
    setDetails((d) => ({ ...d, [key]: value }));

  return (
    <div className="grid gap-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:grid-cols-2">
      <div className="sm:col-span-2">
        <label htmlFor="product-name" className="text-sm font-semibold text-slate-900">
          Product name <span className="text-red-600" aria-hidden="true">*</span>
          <span className="sr-only">(required)</span>
        </label>
        <input
          id="product-name"
          required
          maxLength={80}
          value={details.product_name}
          onChange={(e) => set("product_name", e.target.value)}
          placeholder="e.g. Rose Quartz Ring"
          className={inputClass}
        />
      </div>

      <div>
        <label htmlFor="category" className="text-sm font-semibold text-slate-900">
          Category
        </label>
        <select
          id="category"
          value={details.category}
          onChange={(e) => set("category", e.target.value)}
          className={inputClass}
        >
          <option value="">Choose a category</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="brand-name" className="text-sm font-semibold text-slate-900">
          Brand name <span className="font-normal text-slate-500">(optional)</span>
        </label>
        <input
          id="brand-name"
          maxLength={60}
          value={details.brand_name}
          onChange={(e) => set("brand_name", e.target.value)}
          placeholder="e.g. Luna Studio"
          className={inputClass}
        />
      </div>

      <div className="sm:col-span-2">
        <label htmlFor="description" className="text-sm font-semibold text-slate-900">
          Description
        </label>
        <p id="description-hint" className="mt-0.5 text-xs text-slate-500">
          Facts only: material, size, colours, what is included. The generator uses your words and
          does not invent details.
        </p>
        <textarea
          id="description"
          aria-describedby="description-hint"
          rows={4}
          maxLength={600}
          value={details.description}
          onChange={(e) => set("description", e.target.value)}
          placeholder="e.g. Sterling silver ring with a rose quartz stone. Sizes 5 to 9. Comes in a gift box."
          className={inputClass}
        />
        <p className="mt-1 text-right text-xs text-slate-400">{details.description.length}/600</p>
      </div>

      <div>
        <label htmlFor="audience" className="text-sm font-semibold text-slate-900">
          Target audience
        </label>
        <input
          id="audience"
          maxLength={120}
          value={details.target_audience}
          onChange={(e) => set("target_audience", e.target.value)}
          placeholder="e.g. women who love minimal jewellery"
          className={inputClass}
        />
      </div>

      <div>
        <label htmlFor="offer" className="text-sm font-semibold text-slate-900">
          Offer <span className="font-normal text-slate-500">(optional)</span>
        </label>
        <input
          id="offer"
          maxLength={80}
          value={details.offer}
          onChange={(e) => set("offer", e.target.value)}
          placeholder="e.g. 20% off this weekend"
          className={inputClass}
        />
      </div>

      <fieldset className="sm:col-span-2">
        <legend className="text-sm font-semibold text-slate-900">Tone of voice</legend>
        <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-5">
          {TONES.map((t) => (
            <label
              key={t.value}
              className={`cursor-pointer rounded-lg border px-3 py-2 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-brand-500 ${
                details.tone === t.value
                  ? "border-brand-500 bg-brand-50 text-brand-700"
                  : "border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
            >
              <input
                type="radio"
                name="tone"
                className="sr-only"
                checked={details.tone === t.value}
                onChange={() => set("tone", t.value)}
              />
              <span className="block font-medium">{t.label}</span>
              <span className="block text-xs text-slate-500">{t.hint}</span>
            </label>
          ))}
        </div>
      </fieldset>
    </div>
  );
}
