import type { Metadata } from "next";
import type { CSSProperties, ReactNode } from "react";
import { Figtree, Fraunces } from "next/font/google";

import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display-loaded",
  display: "swap",
});

const ui = Figtree({
  subsets: ["latin"],
  variable: "--font-ui-loaded",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Smart Writer V2",
  description: "Grant draft chat — clarify first, grounded artifact next.",
};

const bodyFontVars = {
  ["--font-display" as string]: "var(--font-display-loaded), serif",
  ["--font-ui" as string]: "var(--font-ui-loaded), sans-serif",
} as CSSProperties;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${ui.variable}`}>
      <body style={bodyFontVars}>{children}</body>
    </html>
  );
}
