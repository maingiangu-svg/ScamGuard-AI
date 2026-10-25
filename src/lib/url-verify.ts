
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
