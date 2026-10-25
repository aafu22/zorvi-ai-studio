export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
  capabilities: {
    llm_provider: boolean;
    background_removal: boolean;
  };
}

export interface UploadedImage {
  id: string;
  width: number;
  height: number;
  format: string;
  size_bytes: number;
  original_url: string;
}

export type Preset = "original" | "square" | "portrait" | "story";
export type Fit = "cover" | "contain";
export type OutputFormat = "png" | "jpeg";

export interface ProcessOptions {
  preset: Preset;
  fit: Fit;
  background: string;
  zoom: number;
  focus_x: number;
  focus_y: number;
  brightness: number;
  contrast: number;
  saturation: number;
  output_format: OutputFormat;
}

/* ------------------------------------------------------------------ copy */

export type Tone = "friendly" | "professional" | "luxury" | "playful" | "festive";
export type Style = "minimal" | "luxury" | "aesthetic" | "festive" | "vibrant";

export interface ProductDetails {
  product_name: string;
  category: string;
  description: string;
  target_audience: string;
  tone: Tone;
  brand_name: string;
  offer: string;
}

export interface CopyRequestBody extends ProductDetails {
  style: Style;
}

export interface ProviderInfo {
  id: string;
  label: string;
  is_ai: boolean;
}

export interface CaptionItem {
  tone: Tone;
  text: string;
}

export interface PromoItem {
  kind: "headline" | "ad" | "story";
  text: string;
}

export interface CopyResponse {
  provider: ProviderInfo;
  captions: CaptionItem[];
  hashtags: string[];
  short_descriptions: string[];
  promos: PromoItem[];
  ctas: string[];
}

/** What the UI edits: same as the response, but hashtags are one editable string. */
export interface CopyDraft extends Omit<CopyResponse, "hashtags"> {
  hashtags: string;
}

/* -------------------------------------------------------------- graphics */

export type GraphicTemplateId = "classic" | "overlay" | "frame" | "offer";
export type GraphicSize = "square" | "portrait" | "story";
export type GraphicFont = "sans" | "serif" | "display";

export interface GraphicColors {
  background: string;
  text: string;
  accent: string;
}

export interface PhotoSettings {
  fit: Fit;
  background: string;
  zoom: number;
  focus_x: number;
  focus_y: number;
  brightness: number;
  contrast: number;
  saturation: number;
}

/** Everything the user can edit in the graphic studio. */
export interface GraphicDraft {
  template: GraphicTemplateId;
  size: GraphicSize;
  font: GraphicFont;
  headline: string;
  subheadline: string;
  cta: string;
  badge: string;
  brand_name: string;
  colors: GraphicColors;
  photo: PhotoSettings;
  /** Draw the Brand Kit logo (ignored by the server if no logo has been uploaded). */
  show_logo: boolean;
  output_format: OutputFormat;
}

export interface GraphicRequestBody extends GraphicDraft {
  image_id: string;
}

export interface GraphicOptions {
  templates: { id: GraphicTemplateId; label: string; description: string; uses_badge: boolean }[];
  sizes: { id: GraphicSize; label: string; width: number; height: number; note: string }[];
  fonts: { id: GraphicFont; label: string }[];
}

/* ------------------------------------------------- brand kit / history / export / demo */

export interface BrandKit {
  brand_name: string;
  colors: GraphicColors;
  font: GraphicFont;
  tone: Tone;
  configured: boolean;
  has_logo: boolean;
  logo_url: string | null;
}

export type BrandKitInput = Pick<BrandKit, "brand_name" | "colors" | "font" | "tone">;

export interface CampaignSummary {
  id: number;
  name: string;
  product_name: string;
  created_at: string;
  thumbnail_url: string;
  photo_url: string;
}

export interface OpenCampaignResponse {
  image: UploadedImage;
  state: Record<string, unknown>;
}

export interface DemoResponse {
  image: UploadedImage;
  details: ProductDetails;
  style: Style;
}

export interface ExportRequestBody {
  image_id: string;
  details: ProductDetails & { style: Style };
  copy: CopyDraft;
  edit: ProcessOptions;
  graphic: GraphicDraft;
  sizes: GraphicSize[];
  include_json: boolean;
}

/* --------------------------------------------------------- AI Marketing Brain */

export type MarketingCategory = "fashion" | "beauty" | "food" | "electronics" | "handmade" | "other";
export type MarketingGoal = "launch" | "sales" | "awareness" | "seasonal" | "engagement";
export type MarketingPlatform = "instagram" | "facebook" | "whatsapp" | "general";
export type MarketingTone = "friendly" | "professional" | "playful" | "elegant" | "persuasive" | "minimal";
export type MarketingSection =
  | "all"
  | "captions"
  | "hashtags"
  | "headlines"
  | "description"
  | "ctas"
  | "promo"
  | "ideas";

export interface MarketingBrief {
  product_name: string;
  description: string;
  category: MarketingCategory;
  price: string;
  offer: string;
  target_audience: string;
  brand_name: string;
  goal: MarketingGoal;
  platform: MarketingPlatform;
  tone: MarketingTone;
}

export interface MarketingRequestBody extends MarketingBrief {
  section: MarketingSection;
}

export interface MarketingContent {
  captions?: string[] | null;
  hashtags?: string[] | null;
  headlines?: string[] | null;
  description?: string | null;
  ctas?: string[] | null;
  promo?: string | null;
  ideas?: string[] | null;
}

export interface MarketingResponse {
  source: { id: "gemini" | "template"; label: string; is_ai: boolean; model: string | null };
  section: MarketingSection;
  content: MarketingContent;
  warnings: string[];
}

/* ------------------------------------------------------------------ auth */

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  email_verified: boolean;
}

export interface SignupResponse {
  user: AuthUser;
  /** True when the account must verify its email first; there is no token in that case. */
  verification_required: boolean;
  token: string | null;
}

export interface MessageResponse {
  message: string;
}

export interface AuthResponse {
  token: string;
  user: AuthUser;
}
