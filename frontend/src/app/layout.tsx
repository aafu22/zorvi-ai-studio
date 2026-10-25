import type { Metadata } from "next";
import type { ReactNode } from "react";

import { AppShell } from "@/components/AppShell";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "Zorvi AI Studio",
  description:
    "Turn one product photo into a complete marketing kit: images, captions, hashtags and social graphics.",
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
