import { SOURCE_META, SENIORITY_LABELS, WORKPLACE_LABELS } from "./labels";
import { formatIsoDate } from "./format";
import {
  SENIORITY_LEVELS,
  SOURCES,
  WORKPLACES,
  type Posting,
  type Seniority,
  type Source,
  type Workplace,
} from "./types";

export const PAGE_SIZE = 20;

export const SORT_KEYS = [
  "first_seen",
  "posted",
  "title",
  "company",
  "source",
  "seniority",
  "workplace",
] as const;

export type SortKey = (typeof SORT_KEYS)[number];
export type SortDir = "asc" | "desc";

export const SORT_LABELS: Record<SortKey, string> = {
  first_seen: "First seen",
  posted: "Posted date",
  title: "Title",
  company: "Company",
  source: "Source",
  seniority: "Seniority",
  workplace: "Workplace",
};

const PARAM_ORDER = [
  "q",
  "seniority",
  "workplace",
  "skill",
  "junior",
  "source",
  "from",
  "to",
  "sort",
  "dir",
  "page",
] as const;

const DAY = /^\d{4}-\d{2}-\d{2}$/;
const QUERY_LIMIT = 200;

const SENIORITY_RANK: Record<Seniority, number> = {
  intern: 0,
  junior: 1,
  mid: 2,
  senior: 3,
  lead: 4,
  staff: 5,
  principal: 6,
  manager: 7,
  unknown: 100,
};

export type SearchParamInput = {
  [key: string]: string | string[] | undefined;
};

export type PostingFilters = {
  q: string;
  seniority: Seniority | null;
  workplace: Workplace | null;
  skill: string | null;
  juniorOnly: boolean;
  source: Source | null;
  from: string | null;
  to: string | null;
  sort: SortKey;
  dir: SortDir;
  page: number;
};

export type SkillChoice = {
  skill: string;
  count: number;
};

export type FilterChip = {
  id: string;
  label: string;
  href: string;
};

export type PostingQueryResult = {
  filters: PostingFilters;
  rows: Posting[];
  total: number;
  matched: number;
  page: number;
  pageCount: number;
  pageSize: number;
  rangeStart: number;
  rangeEnd: number;
  notice: "inverted-range" | null;
  filtered: boolean;
};

function firstString(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function cleanQuery(value: string): string {
  return value.trim().replace(/\s+/g, " ").slice(0, QUERY_LIMIT);
}

function readDay(value: string | string[] | undefined): string | null {
  const text = firstString(value).trim();
  return DAY.test(text) ? text : null;
}

function readChoice<T extends string>(value: string, allowed: readonly T[]): T | null {
  return allowed.includes(value as T) ? (value as T) : null;
}

export function defaultDir(sort: SortKey): SortDir {
  return sort === "first_seen" || sort === "posted" ? "desc" : "asc";
}

export function parsePostingFilters(input: SearchParamInput): PostingFilters {
  const sort = readChoice(firstString(input.sort).trim(), SORT_KEYS) ?? "first_seen";
  const dirText = firstString(input.dir).trim();
  const dir: SortDir = dirText === "asc" || dirText === "desc" ? dirText : defaultDir(sort);
  const pageText = firstString(input.page).trim();
  const parsedPage = Number.parseInt(pageText, 10);
  const page = Number.isInteger(parsedPage) && parsedPage >= 1 ? Math.min(parsedPage, 10_000) : 1;
  const junior = firstString(input.junior).trim();
  const skill = firstString(input.skill).trim();

  return {
    q: cleanQuery(firstString(input.q)),
    seniority: readChoice(firstString(input.seniority).trim(), SENIORITY_LEVELS),
    workplace: readChoice(firstString(input.workplace).trim(), WORKPLACES),
    skill: skill.length > 0 ? skill : null,
    juniorOnly: junior === "1" || junior === "true",
    source: readChoice(firstString(input.source).trim(), SOURCES),
    from: readDay(input.from),
    to: readDay(input.to),
    sort,
    dir,
    page,
  };
}

/** Recognized params, in canonical order, with blanks dropped. Used to detect a dirty URL. */
export function recognizedSearch(input: SearchParamInput): string {
  const params = new URLSearchParams();
  for (const key of PARAM_ORDER) {
    const raw = firstString(input[key]).trim();
    if (raw.length === 0) {
      continue;
    }
    params.append(key, key === "q" ? cleanQuery(raw) : raw);
  }
  return params.toString();
}

export function filtersToSearchParams(filters: PostingFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q) {
    params.set("q", filters.q);
  }
  if (filters.seniority) {
    params.set("seniority", filters.seniority);
  }
  if (filters.workplace) {
    params.set("workplace", filters.workplace);
  }
  if (filters.skill) {
    params.set("skill", filters.skill);
  }
  if (filters.juniorOnly) {
    params.set("junior", "1");
  }
  if (filters.source) {
    params.set("source", filters.source);
  }
  if (filters.from) {
    params.set("from", filters.from);
  }
  if (filters.to) {
    params.set("to", filters.to);
  }
  const sortIsDefault = filters.sort === "first_seen" && filters.dir === "desc";
  if (!sortIsDefault) {
    params.set("sort", filters.sort);
    params.set("dir", filters.dir);
  }
  if (filters.page > 1) {
    params.set("page", String(filters.page));
  }
  return params;
}

export function filtersHref(filters: PostingFilters, patch: Partial<PostingFilters> = {}): string {
  const next: PostingFilters = { ...filters, ...patch };
  const query = filtersToSearchParams(next).toString();
  return query.length > 0 ? `/?${query}` : "/";
}

export function filtersFromFormData(form: FormData): PostingFilters {
  const read = (key: string): string => {
    const value = form.get(key);
    return typeof value === "string" ? value : "";
  };
  return parsePostingFilters({
    q: read("q"),
    seniority: read("seniority"),
    workplace: read("workplace"),
    skill: read("skill"),
    junior: form.get("junior") === "1" ? "1" : "",
    source: read("source"),
    from: read("from"),
    to: read("to"),
    sort: read("sort"),
    dir: read("dir"),
  });
}

export function formActionHref(form: FormData): string {
  return filtersHref(filtersFromFormData(form), { page: 1 });
}

export function toggledSort(filters: PostingFilters, sort: SortKey): Pick<PostingFilters, "sort" | "dir" | "page"> {
  if (filters.sort !== sort) {
    return { sort, dir: defaultDir(sort), page: 1 };
  }
  return { sort, dir: filters.dir === "asc" ? "desc" : "asc", page: 1 };
}

function isFiltered(filters: PostingFilters): boolean {
  return (
    filters.q.length > 0 ||
    filters.seniority !== null ||
    filters.workplace !== null ||
    filters.skill !== null ||
    filters.juniorOnly ||
    filters.source !== null ||
    filters.from !== null ||
    filters.to !== null
  );
}

function haystack(posting: Posting): string {
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

function matches(posting: Posting, filters: PostingFilters): boolean {
  if (filters.q && !haystack(posting).includes(filters.q.toLowerCase())) {
    return false;
  }
  if (filters.seniority && posting.seniority !== filters.seniority) {
    return false;
  }
  if (filters.workplace && posting.workplace !== filters.workplace) {
    return false;
  }
  if (filters.skill) {
    const needle = filters.skill.toLowerCase();
    if (!posting.skills.some((skill) => skill.toLowerCase() === needle)) {
      return false;
    }
  }
  if (filters.juniorOnly && !posting.junior_friendly) {
    return false;
  }
  if (filters.source && posting.source !== filters.source) {
    return false;
  }
  if (filters.from && posting.first_seen < filters.from) {
    return false;
  }
  if (filters.to && posting.first_seen > filters.to) {
    return false;
  }
  return true;
}

function directed(delta: number, dir: SortDir): number {
  return dir === "asc" ? delta : -delta;
}

function compareText(left: string, right: string, dir: SortDir): number {
  return directed(left.localeCompare(right, "en", { sensitivity: "base", numeric: true }), dir);
}

function compareSeniority(left: Seniority, right: Seniority, dir: SortDir): number {
  const unknownDelta = Number(left === "unknown") - Number(right === "unknown");
  if (unknownDelta !== 0) {
    return unknownDelta;
  }
  return directed(SENIORITY_RANK[left] - SENIORITY_RANK[right], dir);
}

/** Nulls stay last in both directions. */
function compareNullable(left: string | null, right: string | null, dir: SortDir): number {
  if (left === right) {
    return 0;
  }
  if (left === null) {
    return 1;
  }
  if (right === null) {
    return -1;
  }
  return compareText(left, right, dir);
}

function compareBy(left: Posting, right: Posting, sort: SortKey, dir: SortDir): number {
  switch (sort) {
    case "title":
      return compareText(left.title, right.title, dir);
    case "company":
      return compareText(left.company, right.company, dir);
    case "source":
      return compareText(SOURCE_META[left.source].name, SOURCE_META[right.source].name, dir);
    case "workplace":
      return compareText(WORKPLACE_LABELS[left.workplace], WORKPLACE_LABELS[right.workplace], dir);
    case "seniority":
      return compareSeniority(left.seniority, right.seniority, dir);
    case "posted":
      return compareNullable(left.posted_at, right.posted_at, dir);
    case "first_seen":
      return compareText(left.first_seen, right.first_seen, dir);
  }
}

function comparePostings(left: Posting, right: Posting, filters: PostingFilters): number {
  const primary = compareBy(left, right, filters.sort, filters.dir);
  if (primary !== 0) {
    return primary;
  }
  const title = left.title.localeCompare(right.title, "en", { sensitivity: "base", numeric: true });
  if (title !== 0) {
    return title;
  }
  return left.id.localeCompare(right.id);
}

export function queryPostings(postings: readonly Posting[], filters: PostingFilters): PostingQueryResult {
  const inverted = filters.from !== null && filters.to !== null && filters.from > filters.to;
  const matched = inverted ? [] : postings.filter((posting) => matches(posting, filters));
  const sorted = matched.slice().sort((left, right) => comparePostings(left, right, filters));
  const pageCount = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const page = Math.min(filters.page, pageCount);
  const start = (page - 1) * PAGE_SIZE;
  const rows = sorted.slice(start, start + PAGE_SIZE);
  return {
    filters: { ...filters, page },
    rows,
    total: postings.length,
    matched: sorted.length,
    page,
    pageCount,
    pageSize: PAGE_SIZE,
    rangeStart: sorted.length === 0 ? 0 : start + 1,
    rangeEnd: start + rows.length,
    notice: inverted ? "inverted-range" : null,
    filtered: isFiltered(filters),
  };
}

export function skillChoices(postings: readonly Posting[]): SkillChoice[] {
  const counts = new Map<string, number>();
  for (const posting of postings) {
    for (const skill of posting.skills) {
      counts.set(skill, (counts.get(skill) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([skill, count]) => ({ skill, count }))
    .sort((left, right) => right.count - left.count || left.skill.localeCompare(right.skill, "en"));
}

export function dateBounds(postings: readonly Posting[]): { min: string | null; max: string | null } {
  let min: string | null = null;
  let max: string | null = null;
  for (const posting of postings) {
    if (min === null || posting.first_seen < min) {
      min = posting.first_seen;
    }
    if (max === null || posting.first_seen > max) {
      max = posting.first_seen;
    }
  }
  return { min, max };
}

export function pageWindow(page: number, pageCount: number): Array<number | "gap"> {
  if (pageCount <= 7) {
    return Array.from({ length: pageCount }, (_, index) => index + 1);
  }
  const wanted = [1, pageCount, page - 1, page, page + 1].filter(
    (value) => value >= 1 && value <= pageCount,
  );
  const unique = [...new Set(wanted)].sort((left, right) => left - right);
  const window: Array<number | "gap"> = [];
  for (const value of unique) {
    const previous = window[window.length - 1];
    if (typeof previous === "number" && value - previous > 1) {
      window.push("gap");
    }
    window.push(value);
  }
  return window;
}

export function filterChips(filters: PostingFilters): FilterChip[] {
  const chips: FilterChip[] = [];
  const add = (id: string, label: string, patch: Partial<PostingFilters>) => {
    chips.push({ id, label, href: filtersHref(filters, { ...patch, page: 1 }) });
  };
  if (filters.q) {
    add("q", `Search: ${filters.q}`, { q: "" });
  }
  if (filters.seniority) {
    add("seniority", SENIORITY_LABELS[filters.seniority], { seniority: null });
  }
  if (filters.workplace) {
    add("workplace", WORKPLACE_LABELS[filters.workplace], { workplace: null });
  }
  if (filters.skill) {
    add("skill", filters.skill, { skill: null });
  }
  if (filters.juniorOnly) {
    add("junior", "Junior-friendly only", { juniorOnly: false });
  }
  if (filters.source) {
    add("source", SOURCE_META[filters.source].name, { source: null });
  }
  if (filters.from) {
    add("from", `From ${formatIsoDate(filters.from)}`, { from: null });
  }
  if (filters.to) {
    add("to", `To ${formatIsoDate(filters.to)}`, { to: null });
  }
  return chips;
}

export function countSalaryMentions(postings: readonly Posting[]): number {
  return postings.filter((posting) => posting.salary_text !== null && posting.salary_text.length > 0).length;
}
