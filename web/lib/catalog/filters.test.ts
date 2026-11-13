import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  PAGE_SIZE,
  dateBounds,
  filterChips,
  filtersFromFormData,
  countSalaryMentions,
  filtersHref,
  filtersToSearchParams,
  formActionHref,
  pageWindow,
  parsePostingFilters,
  queryPostings,
  recognizedSearch,
  skillChoices,
  toggledSort,
  type PostingFilters,
} from "./filters";
import { formatIsoDate } from "./format";
import type { Posting } from "./types";

function posting(overrides: Partial<Posting> & Pick<Posting, "id" | "title">): Posting {
  return {
    source: "remotive",
    company: "Acme",
    location: "Remote",
    remote: true,
    tags: [],
    salary_text: null,
    posted_at: null,
    url: `https://example.com/jobs/${overrides.id}`,
    fetched_at: "2026-11-12T00:00:00Z",
    seniority: "unknown",
    skills: [],
    workplace: "remote",
    junior_friendly: false,
    regions: [],
    first_seen: "2026-11-10",
    last_seen: "2026-11-12",
    ...overrides,
  };
}

const rows: Posting[] = [
  posting({
    id: "b",
    title: "Senior Python Engineer",
    company: "Beacon",
    seniority: "senior",
    skills: ["Python", "C++"],
    workplace: "remote",
    source: "remoteok",
    first_seen: "2026-11-12",
    posted_at: "2026-11-12T03:00:00Z",
    salary_text: "$100,000",
    tags: ["backend"],
  }),
  posting({
    id: "a",
    title: "Junior Java Developer",
    company: "Acme",
    seniority: "junior",
    skills: ["Java"],
    workplace: "onsite",
    source: "arbeitnow",
    junior_friendly: true,
    first_seen: "2026-11-10",
    posted_at: null,
    location: "Karachi",
  }),
  posting({
    id: "c",
    title: "Intern",
    company: "Cedar",
    seniority: "intern",
    skills: ["Python"],
    workplace: "hybrid",
    source: "remotive",
    junior_friendly: true,
    first_seen: "2026-11-11",
    posted_at: "2026-11-01T00:00:00Z",
  }),
  posting({
    id: "d",
    title: "Engineer",
    company: "Delta",
    seniority: "unknown",
    workplace: "onsite",
    source: "arbeitnow",
    first_seen: "2026-11-10",
  }),
];

describe("parsePostingFilters", () => {
  it("uses newest-first defaults", () => {
    const filters = parsePostingFilters({});
    assert.equal(filters.q, "");
    assert.equal(filters.seniority, null);
    assert.equal(filters.workplace, null);
    assert.equal(filters.skill, null);
    assert.equal(filters.juniorOnly, false);
    assert.equal(filters.source, null);
    assert.equal(filters.from, null);
    assert.equal(filters.to, null);
    assert.equal(filters.sort, "first_seen");
    assert.equal(filters.dir, "desc");
    assert.equal(filters.page, 1);
    assert.equal(filtersToSearchParams(filters).toString(), "");
    assert.equal(filtersHref(filters), "/");
  });

  it("keeps a shareable query and drops values the catalog does not use", () => {
    const filters = parsePostingFilters({
      q: "  machine   learning ",
      seniority: "nope",
      workplace: "remote",
      skill: "C++",
      junior: "true",
      source: ["remotive", "remoteok"],
      from: "2026-11-10",
      to: "not-a-date",
      sort: "title",
      page: "3",
    });
    assert.equal(filters.q, "machine learning");
    assert.equal(filters.seniority, null);
    assert.equal(filters.workplace, "remote");
    assert.equal(filters.skill, "C++");
    assert.equal(filters.juniorOnly, true);
    assert.equal(filters.source, "remotive");
    assert.equal(filters.from, "2026-11-10");
    assert.equal(filters.to, null);
    assert.equal(filters.sort, "title");
    assert.equal(filters.dir, "asc");
    assert.equal(filters.page, 3);
    const canonical = filtersToSearchParams(filters).toString();
    assert.equal(
      canonical,
      "q=machine+learning&workplace=remote&skill=C%2B%2B&junior=1&source=remotive&from=2026-11-10&sort=title&dir=asc&page=3",
    );
    const again = parsePostingFilters(Object.fromEntries(new URLSearchParams(canonical)));
    assert.deepEqual(again, filters);
  });

  it("rejects a non-positive page and caps a huge one", () => {
    assert.equal(parsePostingFilters({ page: "0" }).page, 1);
    assert.equal(parsePostingFilters({ page: "nope" }).page, 1);
    assert.equal(parsePostingFilters({ page: "999999" }).page, 10_000);
  });
});

describe("recognizedSearch", () => {
  it("matches the canonical query once invalid and default params are removed", () => {
    const dirty = { seniority: "nope", junior: "true", sort: "first_seen", dir: "desc", page: "1" };
    const parsed = parsePostingFilters(dirty);
    const canonical = filtersToSearchParams(parsed).toString();
    assert.equal(canonical, "junior=1");
    assert.notEqual(recognizedSearch(dirty), canonical);
    assert.equal(recognizedSearch(Object.fromEntries(new URLSearchParams(canonical))), canonical);
  });
});

describe("queryPostings", () => {
  it("filters by text, skill, workplace, seniority, source, junior-friendly, and dates", () => {
    const python = queryPostings(rows, parsePostingFilters({ q: "PYTHON" }));
    assert.deepEqual(
      python.rows.map((row) => row.id),
      ["b", "c"],
    );

    const skill = queryPostings(rows, parsePostingFilters({ skill: "c++" }));
    assert.deepEqual(
      skill.rows.map((row) => row.id),
      ["b"],
    );

    const junior = queryPostings(rows, parsePostingFilters({ junior: "1", workplace: "onsite" }));
    assert.deepEqual(
      junior.rows.map((row) => row.id),
      ["a"],
    );
    assert.equal(junior.filtered, true);
    assert.equal(junior.matched, 1);
    assert.equal(junior.total, 4);

    const ranged = queryPostings(rows, parsePostingFilters({ from: "2026-11-11", to: "2026-11-11" }));
    assert.deepEqual(
      ranged.rows.map((row) => row.id),
      ["c"],
    );

    const board = queryPostings(rows, parsePostingFilters({ source: "remoteok" }));
    assert.deepEqual(
      board.rows.map((row) => row.id),
      ["b"],
    );

    const level = queryPostings(rows, parsePostingFilters({ seniority: "intern" }));
    assert.deepEqual(
      level.rows.map((row) => row.id),
      ["c"],
    );
  });

  it("sorts seniority with unspecified last, and posted dates with blanks last", () => {
    const seniority = queryPostings(rows, parsePostingFilters({ sort: "seniority", dir: "desc" }));
    assert.deepEqual(
      seniority.rows.map((row) => row.seniority),
      ["senior", "junior", "intern", "unknown"],
    );

    const posted = queryPostings(rows, parsePostingFilters({ sort: "posted", dir: "asc" }));
    assert.deepEqual(
      posted.rows.map((row) => row.id),
      ["c", "b", "d", "a"],
    );
  });

  it("does not mutate the catalog order", () => {
    const input = rows.map((row) => row.id);
    queryPostings(rows, parsePostingFilters({ sort: "title", dir: "asc" }));
    assert.deepEqual(
      rows.map((row) => row.id),
      input,
    );
  });

  it("paginates and clamps a page past the end", () => {
    const many = Array.from({ length: PAGE_SIZE + 1 }, (_, index) =>
      posting({
        id: `row-${index}`,
        title: `Role ${String(index).padStart(2, "0")}`,
        first_seen: "2026-11-10",
      }),
    );
    const first = queryPostings(many, parsePostingFilters({}));
    assert.equal(first.pageCount, 2);
    assert.equal(first.rows.length, PAGE_SIZE);
    assert.equal(first.rangeStart, 1);
    assert.equal(first.rangeEnd, PAGE_SIZE);

    const second = queryPostings(many, parsePostingFilters({ page: "2" }));
    assert.equal(second.rows.length, 1);
    assert.equal(second.rangeStart, PAGE_SIZE + 1);

    const past = queryPostings(many, parsePostingFilters({ page: "9" }));
    assert.equal(past.page, 2);
    assert.equal(past.rows.length, 1);
  });

  it("treats an inverted date range as no matches", () => {
    const result = queryPostings(rows, parsePostingFilters({ from: "2026-11-12", to: "2026-11-10" }));
    assert.equal(result.notice, "inverted-range");
    assert.equal(result.matched, 0);
    assert.equal(result.rows.length, 0);
  });
});

describe("filter helpers", () => {
  it("builds chips that clear one field and reset the page", () => {
    const filters = parsePostingFilters({
      q: "python",
      junior: "1",
      skill: "Python",
      page: "4",
    });
    const chips = filterChips(filters);
    assert.deepEqual(
      chips.map((chip) => chip.label),
      ["Search: python", "Python", "Junior-friendly only"],
    );
    assert.equal(chips[0]?.href, "/?skill=Python&junior=1");
  });

  it("toggles the active column and picks a default direction for a new one", () => {
    const filters: PostingFilters = parsePostingFilters({});
    assert.deepEqual(toggledSort(filters, "first_seen"), { sort: "first_seen", dir: "asc", page: 1 });
    assert.deepEqual(toggledSort(filters, "title"), { sort: "title", dir: "asc", page: 1 });
  });

  it("reads a form and omits empty fields", () => {
    const form = new FormData();
    form.set("q", "java");
    form.set("seniority", "");
    form.set("workplace", "remote");
    form.set("skill", "");
    form.set("source", "");
    form.set("from", "");
    form.set("to", "");
    form.set("sort", "company");
    form.set("dir", "asc");
    form.set("junior", "1");
    assert.equal(formActionHref(form), "/?q=java&workplace=remote&junior=1&sort=company&dir=asc");
    assert.equal(filtersFromFormData(form).page, 1);
  });

  it("counts skills and date bounds", () => {
    assert.deepEqual(skillChoices(rows), [
      { skill: "Python", count: 2 },
      { skill: "C++", count: 1 },
      { skill: "Java", count: 1 },
    ]);
    assert.deepEqual(dateBounds(rows), { min: "2026-11-10", max: "2026-11-12" });
    assert.equal(countSalaryMentions(rows), 1);
  });

  it("windows page numbers", () => {
    assert.deepEqual(pageWindow(1, 3), [1, 2, 3]);
    assert.deepEqual(pageWindow(5, 12), [1, "gap", 4, 5, 6, "gap", 12]);
  });
});

describe("formatIsoDate", () => {
  it("formats snapshot days and posted timestamps", () => {
    assert.equal(formatIsoDate("2026-11-12"), "12 Nov 2026");
    assert.equal(formatIsoDate("2026-11-12", false), "12 Nov");
    assert.equal(formatIsoDate("2026-11-09T09:01:09Z"), "9 Nov 2026");
    assert.equal(formatIsoDate("nope"), "nope");
  });
});
