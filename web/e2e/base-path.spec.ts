import { expect, openHome, test } from "./fixtures";

const basePath = "/junior-job-radar";

test("the static export is served at the GitHub Pages base path", async ({ page }) => {
  const asset = page.waitForResponse(
    (response) => response.url().includes(`${basePath}/_next/`) && response.status() === 200,
  );
  await openHome(page);
  const loaded = await asset;
  expect(new URL(loaded.url()).pathname.startsWith(`${basePath}/_next/`)).toBe(true);
  expect(new URL(loaded.url()).pathname.includes(`${basePath}${basePath}`)).toBe(false);

  const pathname = new URL(page.url()).pathname;
  expect(pathname).toBe(`${basePath}/`);

  const sources = await page.locator("script[src], link[href]").evaluateAll((nodes) =>
    nodes.map((node) => node.getAttribute("src") ?? node.getAttribute("href") ?? ""),
  );
  const prefixed = sources.filter((value) => value.includes("/_next/"));
  expect(prefixed.length).toBeGreaterThan(0);
  expect(prefixed.every((value) => value.startsWith(`${basePath}/_next/`))).toBe(true);
  expect(prefixed.some((value) => value.includes(`${basePath}${basePath}`))).toBe(false);
});
