import { defineConfig, devices } from "@playwright/test";

const ci = Boolean(process.env.CI);

/**
 * Serves the static export under the GitHub Pages base path. `next build`
 * writes `out/` from the committed catalog. Locally the server builds first.
 * CI builds in the workflow, then starts.
 */
const pagesUrl = "http://127.0.0.1:3000/junior-job-radar/";
const start = "node ./scripts/serve-out.mjs";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: ci,
  retries: 0,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [
    ["list"],
    ["html", { open: "never", outputFolder: "playwright-report" }],
  ],
  outputDir: "test-results",
  use: {
    baseURL: pagesUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: ci ? start : `npm run build && ${start}`,
    url: pagesUrl,
    reuseExistingServer: false,
    timeout: ci ? 60_000 : 300_000,
  },
});
