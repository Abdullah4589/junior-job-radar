import { catalog, formatPercent, pageTitles, sortPostings, summaryText } from "./catalog";
import { expect, openHome, summary, tableTitles, test, type Page } from "./fixtures";

function figure(page: Page, label: string) {
  return page
    .getByRole("region", { name: "Headline figures" })
    .locator("[data-slot=card]")
    .filter({ has: page.getByText(label, { exact: true }) });
}

const CHARTS = [
  "New postings on each snapshot day",
  "Postings by seniority",
  "Postings by workplace",
  "Most common skills in the catalog",
] as const;

test("overview shows the catalog figures and charts", async ({ page }) => {
  const requests: string[] = [];
  page.on("request", (request) => {
    requests.push(request.url());
  });

  await openHome(page);

  await expect(figure(page, "Unique postings").locator("p").first()).toHaveText(String(catalog.total));
  await expect(figure(page, "Junior-friendly").locator("p").first()).toHaveText(
    formatPercent(catalog.juniorFriendly, catalog.total),
  );
  await expect(figure(page, "Remote").locator("p").first()).toHaveText(formatPercent(catalog.remote, catalog.total));
  await expect(figure(page, "Salary mentions").locator("p").first()).toHaveText(
    formatPercent(catalog.salaryMentions, catalog.total),
  );

  for (const name of CHARTS) {
    const chart = page.getByRole("img", { name });
    await expect(chart).toBeVisible();
    await expect(chart.locator("svg")).toBeVisible();
  }

  await expect(page.getByRole("heading", { name: "New postings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Seniority" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Workplace" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Top skills" })).toBeVisible();

  const trendTable = page.getByRole("table", { name: "New postings per snapshot day" });
  await expect(trendTable).toBeAttached();
  const firstDay = catalog.days[0]?.date;
  if (!firstDay) {
    throw new Error("Catalog has no snapshot days");
  }
  await expect(trendTable).toContainText(firstDay);

  const ordered = sortPostings(catalog.postings, "first_seen", "desc");
  await expect(summary(page)).toHaveText(summaryText(catalog.total, catalog.total, 1));
  await expect(page.locator("#postings table")).toBeVisible();
  await expect(page.locator("#postings ol")).toBeHidden();
  expect(await tableTitles(page)).toEqual(pageTitles(ordered));

  const boards = requests.filter((url) => /remotive\.com|remoteok\.com|arbeitnow\.com/i.test(url));
  expect(boards).toEqual([]);
});
