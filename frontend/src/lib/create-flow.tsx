"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type ReactNode,
  type SetStateAction,
} from "react";

import { getBrandKit, uploadImage } from "@/lib/api";
import { getProduct, PRODUCT_HANDOFF_KEY } from "@/lib/product-library";
import { clearBrainHandoff, readBrainHandoff } from "@/lib/brain-handoff";
import type {
  BrandKit,
  CopyDraft,
  GraphicDraft,
  ProcessOptions,
  ProductDetails,
  Style,
  UploadedImage,
} from "@/types/api";

export const DEFAULT_OPTIONS: ProcessOptions = {
  preset: "square",
  fit: "contain",
  background: "#ffffff",
  zoom: 1,
  focus_x: 0.5,
  focus_y: 0.5,
  brightness: 1,
  contrast: 1,
  saturation: 1,
  output_format: "png",
};

export const DEFAULT_DETAILS: ProductDetails = {
  product_name: "",
  category: "",
  description: "",
  target_audience: "",
  tone: "friendly",
  brand_name: "",
  offer: "",
};

const STORAGE_KEY = "zorvi.create-flow.v1";
const STYLES: Style[] = ["minimal", "luxury", "aesthetic", "festive", "vibrant"];

/** Everything the 5-step flow collects. Also the shape saved to history. */
export interface FlowSnapshot {
  step: number;
  image: UploadedImage | null;
  opts: ProcessOptions;
  details: ProductDetails;
  style: Style;
  copy: CopyDraft | null;
  graphic: GraphicDraft | null;
}

const isObject = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);

/**
 * Turn untrusted data (browser storage, or a saved project from the server) into a safe snapshot.
 * Unknown or malformed parts are ignored, and missing parts fall back to defaults, so old
 * saves keep working when new fields are added.
 */
export function normalizeSnapshot(raw: unknown): Partial<FlowSnapshot> {
  if (!isObject(raw)) return {};
  const out: Partial<FlowSnapshot> = {};
  if (typeof raw.step === "number" && raw.step >= 1 && raw.step <= 5) out.step = Math.floor(raw.step);
  if (isObject(raw.image) && typeof raw.image.id === "string") out.image = raw.image as unknown as UploadedImage;
  if (isObject(raw.opts)) out.opts = { ...DEFAULT_OPTIONS, ...(raw.opts as Partial<ProcessOptions>) };
  if (isObject(raw.details)) out.details = { ...DEFAULT_DETAILS, ...(raw.details as Partial<ProductDetails>) };
  if (typeof raw.style === "string" && STYLES.includes(raw.style as Style)) out.style = raw.style as Style;
  if (
    isObject(raw.copy) &&
    Array.isArray(raw.copy.captions) &&
    typeof raw.copy.hashtags === "string" &&
    isObject(raw.copy.provider)
  ) {
    out.copy = raw.copy as unknown as CopyDraft;
  }
  if (isObject(raw.graphic) && typeof raw.graphic.template === "string" && isObject(raw.graphic.colors)) {
    out.graphic = { show_logo: false, ...(raw.graphic as object) } as GraphicDraft;
  }
  return out;
}

function emptySnapshot(): FlowSnapshot {
  return {
    step: 1,
    image: null,
    opts: DEFAULT_OPTIONS,
    details: DEFAULT_DETAILS,
    style: "minimal",
    copy: null,
    graphic: null,
  };
}

/** Prepare the flow before navigating to /create (used by "Try the demo" and "Open" in History). */
export function writeFlowSnapshot(snapshot: Partial<FlowSnapshot>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...emptySnapshot(), ...snapshot }));
  } catch {
    /* storage blocked: the flow will simply start empty */
  }
}

export interface PendingText {
  headline: string;
  subheadline: string;
  cta: string;
}

interface FlowValue {
  hydrated: boolean;
  step: number;
  setStep: Dispatch<SetStateAction<number>>;
  image: UploadedImage | null;
  setImage: Dispatch<SetStateAction<UploadedImage | null>>;
  opts: ProcessOptions;
  setOpts: Dispatch<SetStateAction<ProcessOptions>>;
  details: ProductDetails;
  setDetails: Dispatch<SetStateAction<ProductDetails>>;
  style: Style;
  setStyle: Dispatch<SetStateAction<Style>>;
  copy: CopyDraft | null;
  setCopy: Dispatch<SetStateAction<CopyDraft | null>>;
  graphic: GraphicDraft | null;
  setGraphic: Dispatch<SetStateAction<GraphicDraft | null>>;
  /** The saved Brand Kit, or null while loading / if the server could not be reached. */
  brand: BrandKit | null;
  /** Headline/subheadline/button text waiting to be applied to the graphic (from AI Marketing Brain). */
  pendingText: PendingText | null;
  clearPendingText: () => void;
  /** Replace everything in the flow at once (e.g. start the demo from the upload step). */
  loadSnapshot: (snapshot: Partial<FlowSnapshot>) => void;
  reset: () => void;
}

const FlowContext = createContext<FlowValue | null>(null);

/**
 * Holds everything the 5-step flow collects so steps can share it.
 * Saved in localStorage so your in-progress project survives navigation, refreshes, and closing/reopening the browser on the same device. Browser storage can still be cleared by the user or browser.
 */
export function CreateFlowProvider({ children }: { children: ReactNode }) {
  const [hydrated, setHydrated] = useState(false);
  const [step, setStep] = useState(1);
  const [image, setImage] = useState<UploadedImage | null>(null);
  const [opts, setOpts] = useState<ProcessOptions>(DEFAULT_OPTIONS);
  const [details, setDetails] = useState<ProductDetails>(DEFAULT_DETAILS);
  const [style, setStyle] = useState<Style>("minimal");
  const [copy, setCopy] = useState<CopyDraft | null>(null);
  const [graphic, setGraphic] = useState<GraphicDraft | null>(null);
  const [brand, setBrand] = useState<BrandKit | null>(null);
  const [pendingText, setPendingText] = useState<PendingText | null>(null);
  const brandApplied = useRef(false);

  const loadSnapshot = useCallback((snapshot: Partial<FlowSnapshot>) => {
    const s = { ...emptySnapshot(), ...snapshot };
    setStep(s.step);
    setImage(s.image);
    setOpts(s.opts);
    setDetails(s.details);
    setStyle(s.style);
    setCopy(s.copy);
    setGraphic(s.graphic);
    brandApplied.current = true; // loaded projects keep their own values
  }, []);

  /**
   * Text sent from AI Marketing Brain. It only fills things that are still empty, so nothing the
   * person already did is lost: details only if the project has no product name, copy only if there
   * is none yet, and the graphic's three text fields (applied later by the graphic studio).
   */
  const applyBrainHandoff = useCallback(() => {
    const h = readBrainHandoff();
    if (!h) return;
    setPendingText({ headline: h.headline, subheadline: h.subheadline, cta: h.cta });
    setDetails((d) =>
      d.product_name.trim() === ""
        ? {
            ...d,
            product_name: h.product_name,
            description: h.description,
            brand_name: h.brand_name || d.brand_name,
            offer: h.offer,
            target_audience: h.target_audience,
          }
        : d,
    );
    setCopy((c) => c ?? h.copy);
    brandApplied.current = true;
  }, []);

  const clearPendingText = useCallback(() => {
    setPendingText(null);
    clearBrainHandoff();
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const saved = normalizeSnapshot(JSON.parse(raw));
        if (Object.keys(saved).length > 0) {
          loadSnapshot(saved);
        }
      }
    } catch {
      /* storage unavailable or corrupt: start fresh */
    }
    const handoffId = sessionStorage.getItem(PRODUCT_HANDOFF_KEY);
    if (handoffId) {
      void (async () => {
        try {
          const product = await getProduct(handoffId);
          if (product) {
            const file = new File([product.image], product.name, { type: product.imageType || product.image.type || "image/jpeg" });
            const uploaded = await uploadImage(file);
            setImage(uploaded);
            setStep(2);
            if (product.analysis) {
              setDetails((current) => ({
                ...current,
                product_name: current.product_name || product.analysis!.product_title || product.name.replace(/\.[^.]+$/, ""),
                description: current.description || product.analysis!.visual_description,
                category: current.category || product.analysis!.product_type,
              }));
            } else {
              setDetails((current) => ({ ...current, product_name: current.product_name || product.name.replace(/\.[^.]+$/, "") }));
            }
          }
        } catch {
          /* Keep the normal create flow available if the local product cannot be imported. */
        } finally {
          sessionStorage.removeItem(PRODUCT_HANDOFF_KEY);
        }
      })();
    }
    applyBrainHandoff();
    setHydrated(true);
  }, [loadSnapshot, applyBrainHandoff]);

  // The Brand Kit is optional: if the server is unreachable the flow still works without it.
  useEffect(() => {
    getBrandKit()
      .then(setBrand)
      .catch(() => setBrand(null));
  }, []);

  // A brand-new project starts with your brand name and tone filled in.
  useEffect(() => {
    if (!hydrated || !brand?.configured || brandApplied.current) return;
    brandApplied.current = true;
    setDetails((d) =>
      d.product_name === "" && d.brand_name === "" && !image
        ? { ...d, brand_name: brand.brand_name, tone: brand.tone }
        : d,
    );
  }, [hydrated, brand, image]);

  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ step, image, opts, details, style, copy, graphic }),
      );
    } catch {
      /* ignore: persistence is a convenience only */
    }
  }, [hydrated, step, image, opts, details, style, copy, graphic]);

  const value = useMemo<FlowValue>(
    () => ({
      hydrated,
      step,
      setStep,
      image,
      setImage,
      opts,
      setOpts,
      details,
      setDetails,
      style,
      setStyle,
      copy,
      setCopy,
      graphic,
      setGraphic,
      brand,
      pendingText,
      clearPendingText,
      loadSnapshot,
      reset: () => {
        loadSnapshot(emptySnapshot());
        brandApplied.current = false;
      },
    }),
    [hydrated, step, image, opts, details, style, copy, graphic, brand, pendingText, clearPendingText, loadSnapshot],
  );

  return <FlowContext.Provider value={value}>{children}</FlowContext.Provider>;
}

export function useCreateFlow(): FlowValue {
  const ctx = useContext(FlowContext);
  if (!ctx) throw new Error("useCreateFlow must be used inside CreateFlowProvider");
  return ctx;
}
