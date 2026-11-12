/** Shapes of the committed catalog files. Field names match the pipeline. */

export const SENIORITY_LEVELS = [
  "intern",
  "junior",
  "mid",
  "senior",
  "lead",
  "staff",
  "principal",
  "manager",
  "unknown",
] as const;

export type Seniority = (typeof SENIORITY_LEVELS)[number];

export const WORKPLACES = ["remote", "hybrid", "onsite", "unknown"] as const;

export type Workplace = (typeof WORKPLACES)[number];

export const SOURCES = ["remotive", "remoteok", "arbeitnow"] as const;

export type Source = (typeof SOURCES)[number];

export type SkillCount = {
  skill: string;
  count: number;
};

export type RegionCount = {
  region: string;
  count: number;
};

export type Trends = {
  notes: string;
  postings: number;
  junior_friendly: number;
  top_skills: SkillCount[];
  seniority: Record<Seniority, number>;
  workplace: Record<Workplace, number>;
  regions: RegionCount[];
};

export type Posting = {
  id: string;
  source: Source;
  title: string;
  company: string;
  location: string;
  remote: boolean;
  tags: string[];
  salary_text: string | null;
  posted_at: string | null;
  url: string;
  fetched_at: string;
  seniority: Seniority;
  skills: string[];
  workplace: Workplace;
  junior_friendly: boolean;
  regions: string[];
  first_seen: string;
  last_seen: string;
};

export type SnapshotDay = {
  date: string;
  new: number;
  seen_again: number;
  collected: number;
};

export type Catalog = {
  notes: string;
  postings: Posting[];
  days: SnapshotDay[];
};

export type CatalogBundle = {
  trends: Trends;
  catalog: Catalog;
};
