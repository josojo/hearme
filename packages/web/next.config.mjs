/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    // Server actions are stable in Next 14+; no flag needed but kept for clarity.
  },
};

export default nextConfig;
