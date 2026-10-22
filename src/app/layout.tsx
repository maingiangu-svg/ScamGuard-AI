import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ScamShield Forensic AI — Multimodal Deception & Scam Intelligence",
  description:
    "AI-powered digital forensic analysis and cognitive deception decoding for fraud prevention, engineered with Google Gemini 2.5 Flash.",
  keywords: ["cyber forensic", "scam detection", "phishing intelligence", "Gemini 2.5 Flash", "fraud prevention", "AI security"],
  authors: [{ name: "ScamShield Research Team" }],
  manifest: "/manifest.json",
  openGraph: {
    title: "ScamShield Forensic AI",
    description: "Multimodal digital forensics and cognitive manipulation decoding",
    locale: "en_US",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#FAF8F5",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
