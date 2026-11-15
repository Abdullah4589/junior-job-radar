import {
  catalog,
  dateFilter,
  examplePosting,
  filterPostings,
  pageTitles,
  seniorityFilter,
  skillFilter,
  sourceFilter,
  summaryText,
  workplaceFilter,
  type PostingQuery,
} from "./catalog";
import { applyFilters, expect, expectQuery, openHome, summary, tableTitles, test } from "./fixtures";

async function expectFiltered(page: import("@playwright/test").Page, query: PostingQuery, params: Record<string, string>) {
  await applyFilters(page);
  await expectQuery(page, params);
  const matched = filterPostings(catalog.postings, query);
  await expect(summary(page)).toHaveText(summaryText(matched.length, catalog.total, 1));
  expect(await tableTitles(page)).toEqual(pageTitles(matched));
  expect(matched.length).toBeGreaterThan(0);
  expect(matched.length).toBeLessThan(catalog.total);
}

test("seniority filter updates the table and the query", async ({ page }) => {
  const seniority = seniorityFilter();
  await openHome(page);
  await page.getByRole("combobox", { name: "Seniority" }).selectOption(seniority);
  await expectFiltered(page, { seniority }, { seniority });
  await expect(page.getByRole("list", { name: "Active filters" })).toBeVisible();
});

test("workplace filter updates the table and the query", async ({ page }) => {
  const workplace = workplaceFilter();
  await openHome(page);
  await page.getByRole("combobox", { name: "Workplace" }).selectOption(workplace);
  await expectFiltered(page, { workplace }, { workplace });
});

test("skill filter updates the table and the query", async ({ page }) => {
  const skill = skillFilter();
  await openHome(page);
  await page.getByRole("combobox", { name: "Skill" }).selectOption(skill);
  await expectFiltered(page, { skill }, { skill });
});

test("source filter updates the table and the query", async ({ page }) => {
  const source = sourceFilter();
  await openHome(page);
  await page.getByRole("combobox", { name: "Source" }).selectOption(source.id);
  await expectFiltered(page, { source: source.id }, { source: source.id });
});

test("first-seen dates update the table and the query", async ({ page }) => {
  const day = dateFilter();
  await openHome(page);
  await page.getByLabel("First seen from").fill(day);
  await page.getByLabel("First seen to").fill(day);
  await expectFiltered(page, { from: day, to: day }, { from: day, to: day });
});

test("text search updates the table and the query", async ({ page }) => {
  const example = examplePosting();
  await openHome(page);
  await page.getByRole("searchbox", { name: "Search" }).fill(example.title);
  await expectFiltered(page, { q: example.title }, { q: example.title });
  await expect(page.locator("#postings tbody")).toContainText(example.company);
});

test("junior-friendly only updates the table and the query", async ({ page }) => {
  await openHome(page);
  await page.getByRole("checkbox", { name: /Junior-friendly only/ }).check();
  await expectFiltered(page, { juniorOnly: true }, { junior: "1" });
});

test("filters combine in one query", async ({ page }) => {
  const example = examplePosting();
  const skill = example.skills[0];
  if (!skill) {
    throw new Error("Example posting has no skill");
  }
  await openHome(page);
  await page.getByRole("searchbox", { name: "Search" }).fill(example.title);
  await page.getByRole("combobox", { name: "Seniority" }).selectOption(example.seniority);
  await page.getByRole("combobox", { name: "Workplace" }).selectOption(example.workplace);
  await page.getByRole("combobox", { name: "Skill" }).selectOption(skill);
  await page.getByRole("checkbox", { name: /Junior-friendly only/ }).check();
  await page.getByRole("combobox", { name: "Source" }).selectOption(example.source);
  await page.getByLabel("First seen from").fill(example.first_seen);
  await page.getByLabel("First seen to").fill(example.first_seen);

  const query: PostingQuery = {
    q: example.title,
    seniority: example.seniority,
    workplace: example.workplace,
    skill,
    juniorOnly: true,
    source: example.source,
    from: example.first_seen,
    to: example.first_seen,
  };
  await expectFiltered(page, query, {
    q: example.title,
    seniority: example.seniority,
    workplace: example.workplace,
    skill,
    junior: "1",
    source: example.source,
    from: example.first_seen,
    to: example.first_seen,
  });
  expect(await tableTitles(page)).toEqual([example.title]);
});
