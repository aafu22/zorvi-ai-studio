import type {
  AuthResponse,
  AuthUser,
  BrandKit,
  BrandKitInput,
  CampaignSummary,
  CopyRequestBody,
  DemoResponse,
  ExportRequestBody,
  OpenCampaignResponse,
  CopyResponse,
  GraphicOptions,
  GraphicRequestBody,
  HealthResponse,
  MessageResponse,
  MarketingRequestBody,
  MarketingResponse,
  ProcessOptions,
  SignupResponse,
  UploadedImage,
} from "@/types/api";

/** The single configurable backend URL. All API calls go through request(). */
export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Where the browser keeps the sign-in token (see lib/auth.tsx). */
export const TOKEN_KEY = "zorvi_auth_token";

function storedToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

/** Add the sign-in token (when there is one) to a request. Only ever sent to our own backend, via request(). */
function withAuth(init?: RequestInit): RequestInit | undefined {
  const token = storedToken();
  if (!token) return init;
  const headers = new Headers(init?.headers);
  if (!headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  return { ...init, headers };
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, withAuth(init));
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(
      `Cannot reach the backend at ${API_URL}. Is it running?`,
      0,
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body?.detail)) {
        detail = "Some settings were invalid.";
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail || "Request failed", res.status);
  }
  return res;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  return (await (await request(path, init)).json()) as T;
}

/**
 * Download a protected file (saved photo, thumbnail, logo) with the sign-in token.
 * <img src> and <a href> cannot send an Authorization header, so private images are fetched this way.
 */
export async function fetchBlob(path: string): Promise<Blob> {
  return (await request(path)).blob();
}

export const getHealth = () => apiFetch<HealthResponse>("/api/health");

export function uploadImage(file: File): Promise<UploadedImage> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<UploadedImage>("/api/images/upload", {
    method: "POST",
    body: form,
  });
}

export async function processImage(
  id: string,
  options: ProcessOptions,
  signal?: AbortSignal,
): Promise<Blob> {
  const res = await request(`/api/images/${id}/process`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(options),
    signal,
  });
  return res.blob();
}

export async function deleteImage(id: string): Promise<void> {
  await request(`/api/images/${id}`, { method: "DELETE" });
}

export const originalImageUrl = (image: UploadedImage) =>
  `${API_URL}${image.original_url}`;

export function generateCopy(body: CopyRequestBody): Promise<CopyResponse> {
  return apiFetch<CopyResponse>("/api/copy/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const getGraphicOptions = () => apiFetch<GraphicOptions>("/api/graphics/options");

/** preview=true returns a smaller image with the identical layout; false returns the 1080 px export. */
export async function renderGraphic(
  body: GraphicRequestBody,
  preview: boolean,
  signal?: AbortSignal,
): Promise<Blob> {
  const res = await request(`/api/graphics/render${preview ? "?preview=true" : ""}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  return res.blob();
}

/* ------------------------------------------------------------- brand kit */

const JSON_HEADERS = { "Content-Type": "application/json" };

export const getBrandKit = () => apiFetch<BrandKit>("/api/brand-kit");

export const saveBrandKit = (kit: BrandKitInput) =>
  apiFetch<BrandKit>("/api/brand-kit", { method: "PUT", headers: JSON_HEADERS, body: JSON.stringify(kit) });

export async function resetBrandKit(): Promise<void> {
  await request("/api/brand-kit", { method: "DELETE" });
}

export function uploadLogo(file: File): Promise<BrandKit> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<BrandKit>("/api/brand-kit/logo", { method: "POST", body: form });
}

export const deleteLogo = () => apiFetch<BrandKit>("/api/brand-kit/logo", { method: "DELETE" });

/** Server path of the signed-in user's logo. Load it with <AuthedImage> or fetchBlob(). */
export const BRAND_LOGO_PATH = "/api/brand-kit/logo";

/* --------------------------------------------------------------- history */

export const listHistory = () => apiFetch<CampaignSummary[]>("/api/history");

export const saveToHistory = (body: {
  image_id: string;
  name: string;
  product_name: string;
  state: Record<string, unknown>;
}) =>
  apiFetch<CampaignSummary>("/api/history", { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });

export const openFromHistory = (id: number) =>
  apiFetch<OpenCampaignResponse>(`/api/history/${id}/open`, { method: "POST" });

export async function deleteFromHistory(id: number): Promise<void> {
  await request(`/api/history/${id}`, { method: "DELETE" });
}

/* ---------------------------------------------------------- export / demo */

export async function exportKit(body: ExportRequestBody): Promise<Blob> {
  const res = await request("/api/export/kit", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
  return res.blob();
}

export const startDemo = () => apiFetch<DemoResponse>("/api/demo/start", { method: "POST" });

/* ------------------------------------------------------ AI Marketing Brain */

export const generateMarketing = (body: MarketingRequestBody, signal?: AbortSignal) =>
  apiFetch<MarketingResponse>("/api/marketing/generate", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
    signal,
  });

/** Rule-based draft. Always labelled template-based; works without an API key. */
export const generateMarketingTemplate = (body: MarketingRequestBody) =>
  apiFetch<MarketingResponse>("/api/marketing/template", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });

/** AI Photo Assistant. Needs sign-in; the caller supplies the result type. */
export function analyzePhoto<T>(file: File, signal?: AbortSignal): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<T>("/api/photo-assistant/analyze", { method: "POST", body: form, signal });
}

/* ------------------------------------------------------------------ auth */

export const apiSignup = (body: { name: string; email: string; password: string }) =>
  apiFetch<SignupResponse>("/api/auth/signup", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });

export const apiLogin = (body: { email: string; password: string }) =>
  apiFetch<AuthResponse>("/api/auth/login", {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });

export const apiMe = (token: string) =>
  apiFetch<AuthUser>("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } });

export async function apiLogout(token: string): Promise<void> {
  await request("/api/auth/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

const postJson = <T,>(path: string, body: unknown) =>
  apiFetch<T>(path, { method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body) });

export const apiVerifyEmail = (token: string) =>
  postJson<MessageResponse>("/api/auth/verify-email", { token });

export const apiResendVerification = (email: string) =>
  postJson<MessageResponse>("/api/auth/resend-verification", { email });

export const apiForgotPassword = (email: string) =>
  postJson<MessageResponse>("/api/auth/forgot-password", { email });

export const apiResetPassword = (token: string, password: string) =>
  postJson<MessageResponse>("/api/auth/reset-password", { token, password });
