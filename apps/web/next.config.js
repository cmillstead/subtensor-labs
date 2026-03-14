/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@subtensor-labs/shared"],
  // NOTE: Engine proxying is handled by API route handlers in src/app/api/proxy/,
  // NOT by Next.js rewrites, because rewrites bake the destination URL at build time.
  // ENGINE_URL is read at runtime in engine-client.ts for server-side fetches.
  headers: async () => [
    {
      source: "/(.*)",
      headers: [
        { key: "X-Frame-Options", value: "DENY" },
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        {
          key: "Content-Security-Policy",
          value:
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'",
        },
        {
          key: "Strict-Transport-Security",
          value: "max-age=63072000; includeSubDomains",
        },
        {
          key: "Permissions-Policy",
          value: "camera=(), microphone=(), geolocation=()",
        },
      ],
    },
  ],
};

module.exports = nextConfig;
