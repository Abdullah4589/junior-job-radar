import { defineConfig, devices } from "@playwright/test";

const ci = Boolean(process.env.CI);

/**
 * Serves the production build. `next start` reads the catalog that `next build`
 * compiled in, so the tests exercise the committed data and not a dev server.
 * Locally the server builds first. CI builds in the workflow, then starts.
 */
const start = "npm run start -- --hostname 127.0.0.1 --port 3000";

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
    baseURL: "http://127.0.0.1:3000",
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
    url: "http://127.0.0.1:3000",
    reuseExistingServer: false,
    timeout: ci ? 60_000 : 300_000,
  },
});
