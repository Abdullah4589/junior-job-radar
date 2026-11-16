import type { NextConfig } from "next";

/**
 * Project site: https://abdullah4589.github.io/junior-job-radar/
 * `basePath` prefixes routes. `assetPrefix` prefixes `/_next` assets the same
 * way, so a Pages deploy (artifact root = site root) can load the JS and CSS.
 * No trailing slash on either value; Next adds the slash itself.
 */
const repositoryBasePath = "/junior-job-radar";

const nextConfig: NextConfig = {
  // Static files in web/out. Cache Components stay off: Next.js refuses
  // Partial Prerendering when output is "export".
  output: "export",
  basePath: repositoryBasePath,
  assetPrefix: repositoryBasePath,
  trailingSlash: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
