/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: builds to `out/`, served by nginx (see Dockerfile).
  output: 'export',
  reactStrictMode: true,
  // Required for `output: 'export'` (no server-side image optimization).
  images: { unoptimized: true },
  // Trailing slashes make static hosting/deep links behave predictably.
  trailingSlash: true,
};

export default nextConfig;
