import {
  FolderOpen,
  History,
  LayoutDashboard,
  Palette,
  ScanSearch,
  Sparkles,
  Wand2,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Create Content", href: "/create", icon: Wand2 },
  { label: "AI Marketing Brain", href: "/marketing-brain", icon: Sparkles },
  { label: "AI Photo Assistant", href: "/photo-assistant", icon: ScanSearch },
  { label: "Brand Kit", href: "/brand-kit", icon: Palette },
  { label: "My Assets", href: "/assets", icon: FolderOpen },
  { label: "History", href: "/history", icon: History },
];

export const CREATION_STEPS = [
  { title: "Upload product", description: "Add one clear product photo." },
  { title: "Add details", description: "Name, category, audience and tone." },
  { title: "Choose a style", description: "Minimal, luxury, festive and more." },
  { title: "Generate content", description: "Captions, hashtags and graphics." },
  { title: "Preview & export", description: "Edit, download or export a ZIP." },
] as const;
