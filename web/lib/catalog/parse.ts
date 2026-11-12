import {
  SENIORITY_LEVELS,
  SOURCES,
  WORKPLACES,
  type Catalog,
  type Posting,
  type RegionCount,
  type Seniority,
  type SkillCount,
  type SnapshotDay,
  type Source,
  type Trends,
  type Workplace,
} from "@/lib/catalog/types";

const DAY = /^\d{4}-\d{2}-\d{2}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function expectRecord(value: unknown, where: string): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new Error(`${where} must be an object`);
  }
  return value;
}

function expectString(record: Record<string, unknown>, key: string, where: string): string {
  const value = record[key];
  if (typeof value !== "string" || value.length === 0) {
    throw new Error(`${where}.${key} must be a non-empty string`);
  }
  return value;
}

function expectNotes(record: Record<string, unknown>, where: string): string {
  const value = record.notes;
  if (typeof value !== "string") {
    throw new Error(`${where}.notes must be a string`);
  }
  return value;
}

function expectCount(record: Record<string, unknown>, key: string, where: string): number {
  const value = record[key];
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    throw new Error(`${where}.${key} must be a non-negative integer`);
  }
  return value;
}

function expectBoolean(record: Record<string, unknown>, key: string, where: string): boolean {
  const value = record[key];
  if (typeof value !== "boolean") {
    throw new Error(`${where}.${key} must be a boolean`);
  }
  return value;
}

function expectDay(value: unknown, where: string): string {
  if (typeof value !== "string" || !DAY.test(value)) {
    throw new Error(`${where} must be a YYYY-MM-DD date`);
  }
  return value;
}

function expectUrl(value: unknown, where: string): string {
  if (typeof value !== "string" || !/^https?:\/\//.test(value)) {
    throw new Error(`${where} must be an http(s) URL`);
  }
  return value;
}

function expectNullableText(
  record: Record<string, unknown>,
  key: string,
  where: string,
): string | null {
  const value = record[key];
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value !== "string") {
    throw new Error(`${where}.${key} must be a string or null`);
  }
  return value.length === 0 ? null : value;
}

function expectStringList(value: unknown, where: string, { allowMissing }: { allowMissing: boolean }): string[] {
  if (value === undefined && allowMissing) {
    return [];
  }
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item.length === 0)) {
    throw new Error(`${where} must be a list of non-empty strings`);
  }
  return value;
}

function expectChoice<T extends string>(
  value: unknown,
  allowed: readonly T[],
  where: string,
  fallback: T | undefined,
): T {
  if ((value === undefined || value === null) && fallback !== undefined) {
    return fallback;
  }
  if (typeof value === "string" && allowed.includes(value as T)) {
    return value as T;
  }
  throw new Error(`${where} must be one of: ${allowed.join(", ")}`);
}

function expectCountMap<T extends string>(
  value: unknown,
  keys: readonly T[],
  where: string,
): Record<T, number> {
  const record = expectRecord(value, where);
  const extra = Object.keys(record).filter((key) => !keys.includes(key as T));
  if (extra.length > 0) {
    throw new Error(`${where} has unexpected keys: ${extra.join(", ")}`);
  }
  const counts = {} as Record<T, number>;
  for (const key of keys) {
    counts[key] = expectCount(record, key, where);
  }
  return counts;
}

function expectNamedCounts(
  value: unknown,
  nameKey: "skill" | "region",
  where: string,
): Array<{ name: string; count: number }> {
  if (!Array.isArray(value)) {
    throw new Error(`${where} must be a list`);
  }
  return value.map((item, index) => {
    const row = expectRecord(item, `${where}[${index}]`);
    return {
      name: expectString(row, nameKey, `${where}[${index}]`),
      count: expectCount(row, "count", `${where}[${index}]`),
    };
  });
}

export function parseTrends(value: unknown): Trends {
  const record = expectRecord(value, "trends.json");
  const skills = expectNamedCounts(record.top_skills, "skill", "trends.json.top_skills");
  const regions = expectNamedCounts(record.regions, "region", "trends.json.regions");
  return {
    notes: expectNotes(record, "trends.json"),
    postings: expectCount(record, "postings", "trends.json"),
    junior_friendly: expectCount(record, "junior_friendly", "trends.json"),
    top_skills: skills.map((row): SkillCount => ({ skill: row.name, count: row.count })),
    seniority: expectCountMap(record.seniority, SENIORITY_LEVELS, "trends.json.seniority"),
    workplace: expectCountMap(record.workplace, WORKPLACES, "trends.json.workplace"),
    regions: regions.map((row): RegionCount => ({ region: row.name, count: row.count })),
  };
}

function parsePosting(value: unknown, index: number): Posting {
  const where = `postings.json.postings[${index}]`;
  const record = expectRecord(value, where);
  const seniority = expectChoice<Seniority>(
    record.seniority,
    SENIORITY_LEVELS,
    `${where}.seniority`,
    "unknown",
  );
  const juniorFriendly =
    record.junior_friendly === undefined
      ? seniority === "intern" || seniority === "junior"
      : expectBoolean(record, "junior_friendly", where);
  return {
    id: expectString(record, "id", where),
    source: expectChoice<Source>(record.source, SOURCES, `${where}.source`, undefined),
    title: expectString(record, "title", where),
    company: expectString(record, "company", where),
    location: expectString(record, "location", where),
    remote: expectBoolean(record, "remote", where),
    tags: expectStringList(record.tags, `${where}.tags`, { allowMissing: false }),
    salary_text: expectNullableText(record, "salary_text", where),
    posted_at: expectNullableText(record, "posted_at", where),
    url: expectUrl(record.url, `${where}.url`),
    fetched_at: expectString(record, "fetched_at", where),
    seniority,
    skills: expectStringList(record.skills, `${where}.skills`, { allowMissing: true }),
    workplace: expectChoice<Workplace>(record.workplace, WORKPLACES, `${where}.workplace`, "unknown"),
    junior_friendly: juniorFriendly,
    regions: expectStringList(record.regions, `${where}.regions`, { allowMissing: true }),
    first_seen: expectDay(record.first_seen, `${where}.first_seen`),
    last_seen: expectDay(record.last_seen, `${where}.last_seen`),
  };
}

function parseDay(value: unknown, index: number): SnapshotDay {
  const where = `postings.json.days[${index}]`;
  const record = expectRecord(value, where);
  return {
    date: expectDay(record.date, `${where}.date`),
    new: expectCount(record, "new", where),
    seen_again: expectCount(record, "seen_again", where),
    collected: expectCount(record, "collected", where),
  };
}

export function parseCatalog(value: unknown): Catalog {
  const record = expectRecord(value, "postings.json");
  if (!Array.isArray(record.postings)) {
    throw new Error("postings.json.postings must be a list");
  }
  if (!Array.isArray(record.days)) {
    throw new Error("postings.json.days must be a list");
  }
  return {
    notes: expectNotes(record, "postings.json"),
    postings: record.postings.map((posting, index) => parsePosting(posting, index)),
    days: record.days.map((day, index) => parseDay(day, index)),
  };
}
