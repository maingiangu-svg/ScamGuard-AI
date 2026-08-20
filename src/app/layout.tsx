import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin", "vietnamese"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ScamShield Forensic AI — Giám định Lừa đảo",
  description:
    "Ứng dụng AI phòng chống lừa đảo Việt Nam. Quét ảnh, phân tích tin nhắn/link, giải mã thao túng tâm lý — xây dựng với Google Gemini 2.5 Flash cho AI Riser Vietnam 2026.",
  keywords: ["lừa đảo", "scam", "phishing", "Gemini", "AI Riser Vietnam 2026", "phòng chống lừa đảo"],
  authors: [{ name: "ScamShield Team" }],
  manifest: "/manifest.json",
  openGraph: {
    title: "ScamShield Forensic AI",
    description: "Giám định pháp y số & giải mã thao túng đa phương thức",
    locale: "vi_VN",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#0891b2",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="vi"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
