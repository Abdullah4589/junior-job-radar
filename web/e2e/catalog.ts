import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

/** Same page size as `lib/catalog/filters.ts`. */
export const PAGE_SIZE = 20;

export type CatalogPosting = {
  id: string;
  title: string;
  company: string;
  location: string;
  tags: string[];
  salary_text: string | null;
  seniority: string;
  skills: string[];
  workplace: string;
  junior_friendly: boolean;
  source: string;
  first_seen: string;
  regions: string[];
};

type CatalogFile = {
  postings: CatalogPosting[];
  days: { date: string; new: number }[];
};

type TrendsFile = {
  postings: number;
  junior_friendly: number;
  workplace: { remote: number };
};

export type CatalogSnapshot = {
  postings: CatalogPosting[];
  total: number;
  juniorFriendly: number;
  remote: number;
  salaryMentions: number;
  days: { date: string; new: number }[];
};

export type PostingQuery = {
  q?: string;
  seniority?: string;
  workplace?: string;
  skill?: string;
  juniorOnly?: boolean;
  source?: string;
  from?: string;
  to?: string;
};

const SOURCE_NAMES: Record<string, string> = {
  remotive: "Remotive",
  remoteok: "Remote OK",
  arbeitnow: "Arbeitnow",
};

function catalogFile(name: string): string {
  const candidates = [
    path.resolve(process.cwd(), "..", "data", "catalog", name),
    path.resolve(process.cwd(), "data", "catalog", name),
  ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  throw new Error(`Could not find data/catalog/${name} from ${process.cwd()}`);
}

function readJson<T>(name: string): T {
  return JSON.parse(readFileSync(catalogFile(name), "utf8")) as T;
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatPercent(count: number, total: number): string {
  if (total <= 0) {
    return "n/a";
  }
  return `${((100 * count) / total).toFixed(1)}%`;
}

export function summaryText(matched: number, total: number, page: number): string {
  if (matched === 0) {
    return "No postings match these filters.";
  }
  const start = (page - 1) * PAGE_SIZE + 1;
  const end = Math.min(page * PAGE_SIZE, matched);
  const noun = matched === 1 ? "posting" : "postings";
  const shown = `Showing ${formatCount(start)}–${formatCount(end)} of ${formatCount(matched)} ${noun}`;
  if (matched === total) {
    return `${shown}.`;
  }
  return `${shown}, from ${formatCount(total)} in the catalog.`;
}

function haystack(posting: CatalogPosting): string {
  return [
    posting.title,
    posting.company,
    posting.location,
    posting.salary_text ?? "",
    ...posting.skills,
    ...posting.tags,
    ...posting.regions,
  ]
    .join(" ")
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function compareText(left: string, right: string, dir: "asc" | "desc"): number {
  const delta = left.localeCompare(right, "en", { sensitivity: "base", numeric: true });
  return dir === "asc" ? delta : -delta;
}

export function sortPostings(
  postings: readonly CatalogPosting[],
  sort: "first_seen" | "title",
  dir: "asc" | "desc",
): CatalogPosting[] {
  return postings.slice().sort((left, right) => {
    const primary =
      sort === "title"
        ? compareText(left.title, right.title, dir)
        : compareText(left.first_seen, right.first_seen, dir);
    if (primary !== 0) {
      return primary;
    }
    const title = left.title.localeCompare(right.title, "en", { sensitivity: "base", numeric: true });
    if (title !== 0) {
      return title;
    }
    return left.id.localeCompare(right.id);
  });
}

function matches(posting: CatalogPosting, query: PostingQuery): boolean {
  if (query.q && !haystack(posting).includes(query.q.toLowerCase())) {
    return false;
  }
  if (query.seniority && posting.seniority !== query.seniority) {
    return false;
  }
  if (query.workplace && posting.workplace !== query.workplace) {
    return false;
  }
  if (query.skill && !posting.skills.some((skill) => skill.toLowerCase() === query.skill?.toLowerCase())) {
    return false;
  }
  if (query.juniorOnly && !posting.junior_friendly) {
    return false;
  }
  if (query.source && posting.source !== query.source) {
    return false;
  }
  if (query.from && posting.first_seen < query.from) {
    return false;
  }
  if (query.to && posting.first_seen > query.to) {
    return false;
  }
  return true;
}

export function filterPostings(postings: readonly CatalogPosting[], query: PostingQuery): CatalogPosting[] {
  return sortPostings(
    postings.filter((posting) => matches(posting, query)),
    "first_seen",
    "desc",
  );
}

export function pageTitles(postings: readonly CatalogPosting[], page = 1): string[] {
  const start = (page - 1) * PAGE_SIZE;
  return postings.slice(start, start + PAGE_SIZE).map((posting) => posting.title);
}

function subsetValue(postings: readonly CatalogPosting[], values: readonly string[], read: (posting: CatalogPosting) => string): string {
  for (const value of values) {
    const count = postings.filter((posting) => read(posting) === value).length;
    if (count > 0 && count < postings.length) {
      return value;
    }
  }
  throw new Error(`Catalog has no partial match among ${values.join(", ")}`);
}

export function loadCatalog(): CatalogSnapshot {
  const catalog = readJson<CatalogFile>("postings.json");
  const trends = readJson<TrendsFile>("trends.json");
  const postings = catalog.postings;
  const juniorFriendly = postings.filter((posting) => posting.junior_friendly).length;
  const remote = postings.filter((posting) => posting.workplace === "remote").length;
  if (trends.postings !== postings.length) {
    throw new Error(`trends.json counts ${trends.postings} postings but postings.json has ${postings.length}`);
  }
  if (trends.junior_friendly !== juniorFriendly) {
    throw new Error(`trends.json junior_friendly is ${trends.junior_friendly} but ${juniorFriendly} rows are flagged`);
  }
  if (trends.workplace.remote !== remote) {
    throw new Error(`trends.json remote is ${trends.workplace.remote} but ${remote} rows are remote`);
  }
  return {
    postings,
    total: postings.length,
    juniorFriendly,
    remote,
    salaryMentions: postings.filter((posting) => posting.salary_text !== null && posting.salary_text.length > 0).length,
    days: catalog.days,
  };
}

export const catalog = loadCatalog();

export function seniorityFilter(): string {
  return subsetValue(catalog.postings, ["junior", "intern", "senior"], (posting) => posting.seniority);
}

export function workplaceFilter(): string {
  return subsetValue(catalog.postings, ["remote", "hybrid", "onsite"], (posting) => posting.workplace);
}

export function skillFilter(): string {
  const preferred = ["Python", "Java", "React", "TypeScript", "Docker"];
  for (const skill of preferred) {
    const count = catalog.postings.filter((posting) =>
      posting.skills.some((item) => item.toLowerCase() === skill.toLowerCase()),
    ).length;
    if (count > 0 && count < catalog.total) {
      return skill;
    }
  }
  throw new Error("Catalog has none of the preferred skills");
}

export function sourceFilter(): { id: string; name: string } {
  const id = subsetValue(catalog.postings, ["remotive", "remoteok", "arbeitnow"], (posting) => posting.source);
  const name = SOURCE_NAMES[id];
  if (!name) {
    throw new Error(`Unknown source ${id}`);
  }
  return { id, name };
}

export function dateFilter(): string {
  const counts = new Map<string, number>();
  for (const posting of catalog.postings) {
    counts.set(posting.first_seen, (counts.get(posting.first_seen) ?? 0) + 1);
  }
  const day = [...counts.entries()].find(([, count]) => count > 0 && count < catalog.total);
  if (!day) {
    throw new Error("Catalog dates do not form a partial range");
  }
  return day[0];
}

export function invertedDates(): { from: string; to: string } {
  const dates = catalog.postings.map((posting) => posting.first_seen).sort();
  const from = dates[dates.length - 1] ?? "";
  const to = dates[0] ?? "";
  if (!from || !to || from <= to) {
    throw new Error("Catalog needs two different first-seen dates for the inverted range");
  }
  return { from, to };
}

/** A junior posting whose title matches exactly one row and that names a skill. */
export function examplePosting(): CatalogPosting {
  for (const posting of catalog.postings) {
    const title = posting.title.trim().replace(/\s+/g, " ");
    if (!posting.junior_friendly || posting.skills.length === 0) {
      continue;
    }
    if (title.length < 6 || title.length > 120 || /[&%#?]/.test(title)) {
      continue;
    }
    const needle = title.toLowerCase();
    const hits = catalog.postings.filter((row) => haystack(row).includes(needle));
    if (hits.length === 1) {
      return { ...posting, title };
    }
  }
  throw new Error("Catalog has no junior posting with a unique title and a skill");
}
