import type { NextConfig } from "next";

// All API traffic is proxied to the FastAPI backend so secrets stay server-side and the browser
// talks to a single origin (works locally, on Vercel with an external backend, and on Replit).
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};

export default nextConfig;
