/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      // Proxy API requests to the backend server
      {
        source: '/api/v1/:path*',
        destination: process.env.API_BASE_URL + '/api/v1/:path*',
      },
      // Proxy Swagger UI requests
      {
        source: '/api/docs/spec',
        destination: process.env.API_BASE_URL + '/api/v1/docs/spec',
      },
    ]
  },
  // Allow embedding in iframes (for Swagger UI and Grafana)
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN',
          },
        ],
      },
    ]
  },
}