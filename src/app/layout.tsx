import type { Metadata, Viewport } from "next";
import {connection} from 'next/server';
import {cookies} from 'next/headers';
import "./globals.css";

export const metadata: Metadata = {
  title: "ScamShield Forensic AI — Multimodal Deception & Scam Intelligence",
  description:
    "Local text and URL risk screening using independently trained machine learning models.",
  keywords: ["smishing", "scam detection", "phishing", "local machine learning", "fraud prevention"],
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
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  await connection();
  const preferences = await cookies();
  return (
    <html
      lang={preferences.get('scamguard-language')?.value === 'vi' ? 'vi' : 'en'}
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
