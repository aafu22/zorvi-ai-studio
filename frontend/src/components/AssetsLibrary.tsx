"use client";

import { Download, ImageIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AuthedImage } from "@/components/AuthedImage";
import { SignInPrompt } from "@/components/RequireSignIn";
import { BRAND_LOGO_PATH, fetchBlob, getBrandKit, listHistory } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { saveBlob, slugify } from "@/lib/download";
import type { BrandKit, CampaignSummary } from "@/types/api";
import { deleteProduct, getProducts, PRODUCT_HANDOFF_KEY, type SavedProduct } from "@/lib/product-library";

export function AssetsLibrary() {
  const { user, loading } = useAuth();
  const [items, setItems] = useState<CampaignSummary[] | null>(null);
  const [brand, setBrand] = useState<BrandKit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedProducts, setSavedProducts] = useState<SavedProduct[]>([]);

  // Photo Assistant products live in this browser, so they show for everyone.
  useEffect(() => {
    getProducts()
      .then(setSavedProducts)
      .catch(() => setSavedProducts([]));
  }, []);

  // Saved projects and the brand logo belong to an account.
  useEffect(() => {
    if (loading) return;
    if (!user) {
      setItems([]);
      setBrand(null);
      return;
    }
    Promise.all([listHistory(), getBrandKit()])
      .then(([history, kit]) => {
        setItems(history);
        setBrand(kit);
      })
      .catch((e) => {
        setItems([]);
        setError(e instanceof Error ? e.message : "Could not load your assets.");
      });
  }, [user, loading]);

  const download = async (path: string, filename: string) => {
    setError(null);
    try {
      saveBlob(await fetchBlob(path), filename);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed.");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">My Assets</h1>
        <p className="mt-1 text-sm text-slate-500">
          Your saved product photos and brand logo. Photos you upload but do not save are temporary and
          are deleted automatically. To get graphics and text again, open the project from History and
          export its kit.
        </p>
      </div>

      {error && (
        <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      )}

      <section aria-labelledby="photo-assistant-products" className="space-y-3">
        <div>
          <h2 id="photo-assistant-products" className="text-sm font-semibold text-slate-900">AI Photo Assistant products</h2>
          <p className="mt-1 text-sm text-slate-500">Photos and analysis saved in this browser. They remain available after refresh on this device and browser.</p>
        </div>
        {savedProducts.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-8 text-sm text-slate-500">No saved Photo Assistant products yet. Analyse a photo and it will appear here.</div>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {savedProducts.map((product) => {
              const imageUrl = URL.createObjectURL(product.image);
              return <li key={product.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={imageUrl} alt={product.analysis?.product_title || product.name} className="aspect-square w-full bg-slate-100 object-contain" onLoad={(event) => URL.revokeObjectURL(event.currentTarget.src)} />
                <div className="space-y-2 p-3">
                  <p className="truncate text-sm font-semibold text-slate-900">{product.analysis?.product_title || product.name}</p>
                  <p className="text-xs text-slate-500">{product.analysis ? product.analysis.product_type : "Photo saved · analysis pending"}</p>
                  {product.analysis && <p className="line-clamp-3 text-xs leading-5 text-slate-600">{product.analysis.visual_description}</p>}
                  <div className="grid grid-cols-2 gap-2">
                    <button type="button" onClick={() => { sessionStorage.setItem(PRODUCT_HANDOFF_KEY, product.id); window.location.href = "/create"; }} className="rounded-lg bg-brand-600 px-2 py-2 text-xs font-semibold text-white hover:bg-brand-700">Use in Create</button>
                    <button type="button" onClick={() => { sessionStorage.setItem("zorvi.photo-assistant.current", product.id); window.location.href = "/photo-assistant"; }} className="rounded-lg border border-slate-200 px-2 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">Reopen</button>
                  </div>
                  <button type="button" onClick={() => { if (window.confirm("Delete this saved product and its analysis?")) void deleteProduct(product.id).then(() => getProducts().then(setSavedProducts)); }} className="w-full rounded-lg px-2 py-1.5 text-xs text-red-700 hover:bg-red-50">Delete saved product</button>
                </div>
              </li>;
            })}
          </ul>
        )}
      </section>

      {!loading && !user ? (
        <SignInPrompt
          headingTag="h2"
          feature="saved projects and your logo"
          reason="Saved project photos and your brand logo belong to your account. Sign in to see them."
        />
      ) : items === null ? (
        <div className="h-48 animate-pulse rounded-2xl bg-slate-200" aria-busy="true" />
      ) : (
        <>
          {brand?.has_logo && (
            <section aria-labelledby="logo-heading" className="space-y-3">
              <h2 id="logo-heading" className="text-sm font-semibold text-slate-900">
                Brand logo
              </h2>
              <div className="flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-card">
                <AuthedImage path={BRAND_LOGO_PATH} alt="Your brand logo" className="h-16 w-16 rounded-lg bg-slate-100 object-contain" />
                <button
                  type="button"
                  onClick={() => void download(BRAND_LOGO_PATH, "brand-logo.png")}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50"
                >
                  <Download className="h-4 w-4" aria-hidden="true" />
                  Download logo
                </button>
              </div>
            </section>
          )}

          <section aria-labelledby="photos-heading" className="space-y-3">
            <h2 id="photos-heading" className="text-sm font-semibold text-slate-900">
              Saved product photos
            </h2>
            {items.length === 0 ? (
              <div className="flex flex-col items-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                  <ImageIcon className="h-6 w-6" aria-hidden="true" />
                </span>
                <h3 className="mt-4 text-base font-semibold text-slate-900">Nothing saved yet</h3>
                <p className="mt-1 max-w-md text-sm text-slate-500">
                  Save a project to history and its original photo will be kept here.
                </p>
                <Link
                  href="/create"
                  className="mt-6 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
                >
                  Create content
                </Link>
              </div>
            ) : (
              <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {items.map((c) => (
                  <li key={c.id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
                    <AuthedImage
                      path={c.thumbnail_url}
                      alt={`Photo for ${c.name}`}
                      className="aspect-square w-full bg-slate-100 object-cover"
                    />
                    <div className="p-3">
                      <p className="truncate text-sm font-medium text-slate-900">{c.name}</p>
                      <button
                        type="button"
                        onClick={() =>
                          void download(c.photo_url, `${slugify(c.product_name || c.name)}-original.jpg`)
                        }
                        className="mt-2 inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-800 hover:bg-slate-50"
                      >
                        <Download className="h-3.5 w-3.5" aria-hidden="true" />
                        Download original
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
