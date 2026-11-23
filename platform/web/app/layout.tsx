import "./globals.css";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = { title: "Video Studio", description: "Darija video editing pipeline" };
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#120A1F" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Instrument+Serif:ital@1&display=swap" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}
