import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://zorvi-ai-studio.vercel.app";
const DESCRIPTION =
  "Turn one product photo into a complete marketing kit: images, captions, hashtags and social graphics.";

export const metadata: Metadata = {
  // Needed so the share-preview image gets a full https:// address (LinkedIn and WhatsApp ignore relative ones).
  // The icons and the preview image come from the files icon.svg, favicon.ico, apple-icon.png and
  // opengraph-image.png / twitter-image.png in this folder; Next.js adds the tags for them by itself.
  metadataBase: new URL(SITE_URL),
  title: "Zorvi AI Studio",
  description: DESCRIPTION,
  openGraph: {
    title: "Zorvi AI Studio",
    description: DESCRIPTION,
    siteName: "Zorvi AI Studio",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Zorvi AI Studio",
    description: DESCRIPTION,
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
