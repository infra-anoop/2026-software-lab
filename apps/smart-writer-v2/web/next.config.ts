import type { NextConfig } from "next";

/** Static export so FastAPI can serve the UI same-origin (D5 / T069). */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "export",
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
