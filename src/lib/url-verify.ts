import type { WebIntelligence } from "./types";

const OFFICIAL_DOMAINS: Record<string, string[]> = {
  "Vietcombank": ["vietcombank.com.vn", "vcbdigibank.com.vn"],
  "Shopee": ["shopee.vn", "shopee.com"],
  "Solana": ["solana.com"],
  "Telegram": ["telegram.org", "t.me"],
  "VNeID": ["vneid.gov.vn"],
  "Binance": ["binance.com"],
  "MoMo": ["momo.vn"],
  "Zalo": ["zalo.me", "zalo.vn"],
  "Facebook": ["facebook.com", "fb.com"],
  "Google": ["google.com", "google.com.vn"],
};

export function extractUrls(text: string): string[] {
  const matches = text.match(/https?:\/\/[^\s<>"{}|\\^`[\]]+/gi) || [];
  return [...new Set(matches.map((u) => u.replace(/[.,;:!?)]+$/, "")))];
}

export function getDomain(url: string): string | null {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

export function checkBrandDomain(
  domain: string,
  brandHint?: string | null
): { brand: string | null; officialDomain: string | null; match: "match" | "mismatch" | "unknown" } {
  const normalized = domain.toLowerCase();

  for (const [brand, domains] of Object.entries(OFFICIAL_DOMAINS)) {
    if (domains.some((d) => normalized === d || normalized.endsWith(`.${d}`))) {
      return { brand, officialDomain: domains[0], match: "match" };
    }
  }

  if (brandHint) {
    const hint = brandHint.toLowerCase();
    for (const [brand, domains] of Object.entries(OFFICIAL_DOMAINS)) {
      if (hint.includes(brand.toLowerCase()) || brand.toLowerCase().includes(hint)) {
        const isOfficial = domains.some((d) => normalized === d || normalized.endsWith(`.${d}`));
        return {
          brand,
          officialDomain: domains[0],
          match: isOfficial ? "match" : "mismatch",
        };
      }
    }
  }

  const brandFromDomain = Object.entries(OFFICIAL_DOMAINS).find(([brand]) =>
    normalized.includes(brand.toLowerCase().replace(/\s/g, ""))
  );
  if (brandFromDomain) {
    const [brand, domains] = brandFromDomain;
    const isOfficial = domains.some((d) => normalized === d || normalized.endsWith(`.${d}`));
    return { brand, officialDomain: domains[0], match: isOfficial ? "match" : "mismatch" };
  }

  return { brand: brandHint || null, officialDomain: null, match: "unknown" };
}

export async function verifyUrlLive(url: string): Promise<{
  accessible: boolean;
  statusCode: number | null;
  finalUrl: string | null;
  error: string | null;
}> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const res = await fetch(url, {
      method: "HEAD",
      signal: controller.signal,
      redirect: "follow",
      headers: { "User-Agent": "ScamShield-Forensic/1.0 (+https://github.com/maingiangu-svg/ScamGuard-AI)" },
    });
    clearTimeout(timeout);
    return {
      accessible: res.ok || res.status < 500,
      statusCode: res.status,
      finalUrl: res.url,
      error: null,
    };
  } catch {
    clearTimeout(timeout);
    try {
      const res = await fetch(url, {
        method: "GET",
        signal: AbortSignal.timeout(8000),
        redirect: "follow",
        headers: { "User-Agent": "ScamShield-Forensic/1.0" },
      });
      return {
        accessible: res.ok || res.status < 500,
        statusCode: res.status,
        finalUrl: res.url,
        error: null,
      };
    } catch (err: unknown) {
      return {
        accessible: false,
        statusCode: null,
        finalUrl: null,
        error: err instanceof Error ? err.message : "Không thể kết nối",
      };
    }
  }
}

export async function enrichWebIntelligence(
  webIntel: WebIntelligence | undefined,
  sourceText: string
): Promise<WebIntelligence | undefined> {
  const urls = webIntel?.url ? [webIntel.url] : extractUrls(sourceText);
  if (urls.length === 0) return webIntel;

  const url = urls[0];
  const domain = getDomain(url);
  if (!domain) return webIntel;

  const brandCheck = checkBrandDomain(domain, webIntel?.brand_detected);
  const liveCheck = await verifyUrlLive(url);

  const suspicious: string[] = [...(webIntel?.suspicious_indicators || [])];
  if (brandCheck.match === "mismatch") {
    suspicious.push(`Domain "${domain}" không khớp trang chính thức (${brandCheck.officialDomain})`);
  }
  if (!liveCheck.accessible) {
    suspicious.push(`Không truy cập được URL (HTTP ${liveCheck.statusCode ?? "timeout"})`);
  }
  if (domain.endsWith(".vip") || domain.endsWith(".top") || domain.endsWith(".xyz")) {
    suspicious.push(`TLD rủi ro cao (.${domain.split(".").pop()}) thường dùng cho phishing`);
  }

  return {
    detected: true,
    url,
    domain,
    brand_detected: brandCheck.brand || webIntel?.brand_detected || null,
    domain_match: brandCheck.match !== "unknown" ? brandCheck.match : (webIntel?.domain_match || "unknown"),
    website_status: liveCheck.accessible ? "accessible" : liveCheck.error ? "unavailable" : "unknown",
    suspicious_indicators: [...new Set(suspicious)],
    external_evidence: webIntel?.external_evidence?.length
      ? webIntel.external_evidence
      : brandCheck.officialDomain
        ? [{ title: `Trang chính thức ${brandCheck.brand}`, source_url: `https://${brandCheck.officialDomain}` }]
        : [],
    confidence: Math.min(99, (webIntel?.confidence || 70) + (brandCheck.match === "mismatch" ? 10 : 0)),
    verified_live: liveCheck.accessible,
    http_status: liveCheck.statusCode,
  };
}
