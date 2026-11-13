import type { Seniority, Source, Workplace } from "./types";

export const SENIORITY_LABELS: Record<Seniority, string> = {
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

export const WORKPLACE_LABELS: Record<Workplace, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
  unknown: "Unspecified",
};

export const SOURCE_META: Record<Source, { name: string; href: string }> = {
  remotive: { name: "Remotive", href: "https://remotive.com" },
  remoteok: { name: "Remote OK", href: "https://remoteok.com" },
  arbeitnow: { name: "Arbeitnow", href: "https://www.arbeitnow.com" },
};
