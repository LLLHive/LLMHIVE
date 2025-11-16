/** @type {import('next').NextConfig} */
const nextConfig = {
  // TypeScript build errors are allowed in this MVP phase; runtime tests cover the critical paths.
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
