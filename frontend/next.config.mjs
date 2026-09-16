/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Production optimizations
  output: 'standalone',
  poweredByHeader: false,
  compress: true,
  // NOTE: the `images` block was removed deliberately.
  // It enabled AVIF output and a `hostname: '**'` remote pattern, but the app
  // never uses next/image (product images are served by the backend), so the
  // optimiser was pure attack surface. Removing it drops the AVIF code path
  // implicated in GHSA-2xp9-vwfh-vxw4 and closes the open-image-proxy risk.
  // If remote images are ever needed, add explicit hostnames only.
  //
  // NOTE: Do NOT set NEXT_PUBLIC_API_URL here via `env:`.
  // NEXT_PUBLIC_* vars are inlined at build time from the environment.
  // Setting a fallback here would bake 'http://localhost:8000' into the
  // production bundle. The Dockerfile passes the real URL via build-arg.
  // Experimental features
  experimental: {
    optimizePackageImports: ['recharts', '@tanstack/react-query'],
  },
  // Headers for security
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-DNS-Prefetch-Control', value: 'on' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};

export default nextConfig;
