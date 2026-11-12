import { SENIORITY_LEVELS, WORKPLACES, type Catalog, type Seniority, type Trends, type Workplace } from "@/lib/catalog/types";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"] as const;

const SENIORITY_LABELS: Record<Seniority, string> = {
  intern: "Intern",
  junior: "Junior",
  mid: "Mid",
  senior: "Senior",
  lead: "Lead",
  staff: "Staff",
  principal: "Principal",
  manager: "Manager",
  unknown: "Unspecified",
};

const WORKPLACE_LABELS: Record<Workplace, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
  unknown: "Unspecified",
};

export type DayPoint = {
  date: string;
  label: string;
  new: number;
  seenAgain: number;
  collected: number;
};

export type BreakdownRow = {
  key: string;
  label: string;
  count: number;
  shareLabel: string;
  detail: string;
};

export type SkillRow = {
  skill: string;
  count: number;
  shareLabel: string;
};

export type Overview = {
  totalPostings: number;
  juniorFriendlyCount: number;
  juniorFriendlyShare: string;
  remoteCount: number;
  remoteShare: string;
  snapshotLabel: string;
  days: DayPoint[];
  seniority: BreakdownRow[];
  workplace: BreakdownRow[];
  skills: SkillRow[];
};

export function formatPercent(count: number, total: number): string {
  if (total <= 0) {
    return "n/a";
  }
  return `${((100 * count) / total).toFixed(1)}%`;
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatDay(isoDate: string, includeYear: boolean): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);
  if (!match) {
    return isoDate;
  }
  const year = match[1] ?? isoDate;
  const monthIndex = Number(match[2]) - 1;
  const month = MONTHS[monthIndex];
  const day = Number(match[3]);
  if (!month || !Number.isInteger(day)) {
    return isoDate;
  }
  return includeYear ? `${day} ${month} ${year}` : `${day} ${month}`;
}

function snapshotLabel(dates: string[]): string {
  if (dates.length === 0) {
    return "No snapshot days yet";
  }
  const first = dates[0] ?? "";
  const last = dates[dates.length - 1] ?? first;
  if (first === last) {
    return formatDay(first, true);
  }
  return `${formatDay(first, true)} – ${formatDay(last, true)}`;
}

function sum(values: number[]): number {
  return values.reduce((total, value) => total + value, 0);
}

/**
 * Turn the two catalog files into the overview view model.
 * The files are written together; a mismatch means the page would show two different markets.
 */
export function toOverview(trends: Trends, catalog: Catalog): Overview {
  const total = trends.postings;
  if (total !== catalog.postings.length) {
    throw new Error(
      `trends.json counts ${total} postings but postings.json has ${catalog.postings.length}`,
    );
  }

  const senioritySum = sum(SENIORITY_LEVELS.map((level) => trends.seniority[level]));
  if (senioritySum !== total) {
    throw new Error(`seniority counts sum to ${senioritySum}, expected ${total}`);
  }

  const workplaceSum = sum(WORKPLACES.map((place) => trends.workplace[place]));
  if (workplaceSum !== total) {
    throw new Error(`workplace counts sum to ${workplaceSum}, expected ${total}`);
  }

  const newSum = sum(catalog.days.map((day) => day.new));
  if (newSum !== total) {
    throw new Error(`days.new sums to ${newSum}, expected ${total}`);
  }

  const juniorFromRows = catalog.postings.filter((posting) => posting.junior_friendly).length;
  if (juniorFromRows !== trends.junior_friendly) {
    throw new Error(
      `trends.json junior_friendly is ${trends.junior_friendly} but ${juniorFromRows} postings are flagged`,
    );
  }

  const juniorFromLevels = trends.seniority.intern + trends.seniority.junior;
  if (juniorFromLevels !== trends.junior_friendly) {
    throw new Error(
      `junior_friendly is ${trends.junior_friendly} but intern + junior is ${juniorFromLevels}`,
    );
  }

  const days = [...catalog.days].sort((left, right) => left.date.localeCompare(right.date));
  const dates = days.map((day) => day.date);
  const spanYears = (dates[0]?.slice(0, 4) ?? "") !== (dates[dates.length - 1]?.slice(0, 4) ?? "");

  return {
    totalPostings: total,
    juniorFriendlyCount: trends.junior_friendly,
    juniorFriendlyShare: formatPercent(trends.junior_friendly, total),
    remoteCount: trends.workplace.remote,
    remoteShare: formatPercent(trends.workplace.remote, total),
    snapshotLabel: snapshotLabel(dates),
    days: days.map((day) => ({
      date: day.date,
      label: formatDay(day.date, spanYears),
      new: day.new,
      seenAgain: day.seen_again,
      collected: day.collected,
    })),
    seniority: SENIORITY_LEVELS.map((level) => ({
      key: level,
      label: SENIORITY_LABELS[level],
      count: trends.seniority[level],
      shareLabel: formatPercent(trends.seniority[level], total),
      detail: `${trends.seniority[level]} · ${formatPercent(trends.seniority[level], total)}`,
    })),
    workplace: WORKPLACES.map((place) => ({
      key: place,
      label: WORKPLACE_LABELS[place],
      count: trends.workplace[place],
      shareLabel: formatPercent(trends.workplace[place], total),
      detail: `${trends.workplace[place]} · ${formatPercent(trends.workplace[place], total)}`,
    })),
    skills: trends.top_skills.map((row) => ({
      skill: row.skill,
      count: row.count,
      shareLabel: formatPercent(row.count, total),
    })),
  };
}
