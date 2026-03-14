/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ["@subtensor-labs/shared"],
  // NOTE: Engine proxying is handled by API route handlers in src/app/api/proxy/,
  // NOT by Next.js rewrites, because rewrites bake the destination URL at build time.
  // ENGINE_URL is read at runtime in engine-client.ts for server-side fetches.
};

module.exports = nextConfig;
