import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import { Providers } from "@/components/Providers";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const space = Space_Grotesk({ subsets: ["latin"], variable: "--font-space", weight: ["500", "600", "700"], display: "swap" });

export const metadata: Metadata = {
  title: "CoverClaim — hacks happen, claims shouldn't be a vote",
  description:
    "DeFi hack insurance where claims are judged by GenLayer validators against frozen policy wording. GenLayer reads public incident evidence and classifies it against the frozen policy's covered perils and exclusions. Deterministic contract logic enforces capacity, waiting periods, backdating checks, premium accounting, severity payouts, deductibles, and pro-rata splits.",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = { themeColor: "#0B0B0F", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${space.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
