import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingExcludes: {
    "/api/*": ["./ml_model/data/**/*", "./.venv/**/*", "./.local-runtime/**/*"],
  },
  outputFileTracingIncludes: {
    "/api/*": ["./ml_model/*.py", "./ml_model/models/*bundle.pkl", "./ml_model/models/hybrid_manifest.json"],
  },
  poweredByHeader: false,
  headers: () => [{
    source: "/:path*",
    headers: [
      {key: "X-Content-Type-Options", value: "nosniff"},
      {key: "X-Frame-Options", value: "DENY"},
      {key: "Referrer-Policy", value: "no-referrer"},
      {key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()"},
      {key: "Content-Security-Policy", value: "default-src 'none'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'"},
    ],
  }],
};

export default nextConfig;
