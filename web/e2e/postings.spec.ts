import { catalog, invertedDates, PAGE_SIZE, pageTitles, sortPostings, summaryText } from "./catalog";
import { cardTitles, expect, expectQuery, openHome, summary, tableTitles, test } from "./fixtures";

test("unknown query values are replaced with the canonical catalog url", async ({ page }) => {
  await page.goto("./?seniority=nope&extra=1");
  await expect(page).toHaveURL((url) => [...url.searchParams.keys()].length === 0);
  await expect(page.getByRole("heading", { name: "Junior Job Radar", level: 1 })).toBeVisible();
  await expect(summary(page)).toHaveText(summaryText(catalog.total, catalog.total, 1));
});

test("pagination moves to the next page of the catalog", async ({ page }) => {
  const ordered = sortPostings(catalog.postings, "first_seen", "desc");
  await openHome(page);
  await expect(page.getByRole("navigation", { name: "Postings pages" })).toBeVisible();
  expect(await tableTitles(page)).toEqual(pageTitles(ordered, 1));

  await page.getByRole("link", { name: "Next", exact: true }).click();
  await expectQuery(page, { page: "2" });
  await expect(summary(page)).toHaveText(summaryText(catalog.total, catalog.total, 2));
  expect(await tableTitles(page)).toEqual(pageTitles(ordered, 2));
  expect(pageTitles(ordered, 2)[0]).not.toBe(pageTitles(ordered, 1)[0]);
  expect(ordered.length).toBeGreaterThan(PAGE_SIZE);
});

test("sorting by role orders the table and the query", async ({ page }) => {
  await openHome(page);
  await page.getByRole("link", { name: "Sort by Role" }).click();
  await expectQuery(page, { sort: "title", dir: "asc" });
  const ordered = sortPostings(catalog.postings, "title", "asc");
  await expect(summary(page)).toHaveText(summaryText(catalog.total, catalog.total, 1));
  expect(await tableTitles(page)).toEqual(pageTitles(ordered));
  await expect(page.getByRole("columnheader", { name: /Role/ })).toHaveAttribute("aria-sort", "ascending");
});

test("a search with no matches shows the empty state", async ({ page }) => {
  const missing = "zzznomatchjuniorjobradar";
  await openHome(page);
  await page.getByRole("searchbox", { name: "Search" }).fill(missing);
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expectQuery(page, { q: missing });
  await expect(summary(page)).toHaveText("No postings match these filters.");
  await expect(page.getByText("No postings match these filters.")).toHaveCount(2);
  await expect(page.getByRole("link", { name: "Clear filters" })).toBeVisible();
  await expect(page.locator("#postings tbody tr")).toHaveCount(0);
});

test("a start date after the end date explains the empty range", async ({ page }) => {
  const range = invertedDates();
  await openHome(page);
  await page.getByLabel("First seen from").fill(range.from);
  await page.getByLabel("First seen to").fill(range.to);
  await page.getByRole("button", { name: "Apply filters" }).click();
  await expectQuery(page, { from: range.from, to: range.to });
  await expect(summary(page)).toHaveText("The start date is after the end date.");
  await expect(page.locator("#postings").getByRole("alert")).toHaveText(
    "The start date is after the end date. Swap the dates, or clear the filters.",
  );
  await expect(page.locator("#postings tbody tr")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Clear filters" })).toBeVisible();
});

test.describe("mobile", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("shows a card for each posting instead of the table", async ({ page }) => {
    const ordered = sortPostings(catalog.postings, "first_seen", "desc");
    await openHome(page);
    const list = page.locator("#postings ol");
    await expect(list).toBeVisible();
    await expect(page.locator("#postings table")).toBeHidden();
    expect(await cardTitles(page)).toEqual(pageTitles(ordered));
    await expect(list.locator("li").first()).toContainText(ordered[0]?.company ?? "");
    await expect(summary(page)).toHaveText(summaryText(catalog.total, catalog.total, 1));
  });
});
