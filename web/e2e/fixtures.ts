import { test as base, expect, type Page } from "@playwright/test";

const JOB_BOARDS = /https?:\/\/([^/?#]*\.)?(remotive\.com|remoteok\.com|arbeitnow\.com)([:/?#]|$)/i;

export const test = base.extend({
  page: async ({ page }, apply) => {
    const leaked: string[] = [];
    await page.route(JOB_BOARDS, async (route) => {
      leaked.push(route.request().url());
      await route.abort();
    });
    await apply(page);
    expect(leaked, "the dashboard must not call Remotive, Remote OK, or Arbeitnow").toEqual([]);
  },
});

export { expect };
export type { Page };

export function summary(page: Page) {
  return page.locator("#postings [aria-live='polite']");
}

export async function openHome(page: Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Junior Job Radar", level: 1 })).toBeVisible();
  await expect(summary(page)).toBeVisible();
}

export async function applyFilters(page: Page) {
  await page.getByRole("button", { name: "Apply filters" }).click();
}

function cleanTitle(text: string): string {
  return text.replace(/\(opens in a new tab\)/g, "").replace(/\s+/g, " ").trim();
}

export async function tableTitles(page: Page): Promise<string[]> {
  const rows = page.locator("#postings tbody tr");
  const count = await rows.count();
  const titles: string[] = [];
  for (let index = 0; index < count; index += 1) {
    const text = await rows.nth(index).locator("td").first().locator("a").first().textContent();
    titles.push(cleanTitle(text ?? ""));
  }
  return titles;
}

export async function cardTitles(page: Page): Promise<string[]> {
  const cards = page.locator("#postings ol li");
  const count = await cards.count();
  const titles: string[] = [];
  for (let index = 0; index < count; index += 1) {
    const text = await cards.nth(index).locator("a").first().textContent();
    titles.push(cleanTitle(text ?? ""));
  }
  return titles;
}

export async function expectQuery(page: Page, query: Record<string, string>) {
  await expect(page).toHaveURL((url) => {
    const actual = [...url.searchParams.entries()];
    const expected = Object.entries(query);
    return (
      actual.length === expected.length &&
      actual.every(([key, value], index) => key === expected[index]?.[0] && value === expected[index]?.[1])
    );
  });
}
