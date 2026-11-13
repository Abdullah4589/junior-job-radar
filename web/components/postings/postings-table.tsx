import Link from "next/link";

import { ExternalLink, textLinkClass } from "@/components/text-link";
import { Badge } from "@/components/ui/badge";
import { filtersHref, toggledSort, type PostingFilters, type SortKey } from "@/lib/catalog/filters";
import { formatIsoDate } from "@/lib/catalog/format";
import { SENIORITY_LABELS, SOURCE_META, WORKPLACE_LABELS } from "@/lib/catalog/labels";
import type { Posting } from "@/lib/catalog/types";

function SortHeader({
  label,
  sortKey,
  filters,
}: {
  label: string;
  sortKey: SortKey;
  filters: PostingFilters;
}) {
  const next = toggledSort(filters, sortKey);
  const active = filters.sort === sortKey;
  const direction = filters.dir === "asc" ? "ascending" : "descending";
  return (
    <th
      scope="col"
      aria-sort={active ? direction : "none"}
      className="px-3 py-3 text-left font-medium whitespace-nowrap"
    >
      <Link
        href={filtersHref(filters, next)}
        scroll={false}
        aria-label={
          active ? `Sort by ${label}, currently ${direction}. Activate to reverse.` : `Sort by ${label}`
        }
        className={textLinkClass}
      >
        {label}
        {active ? <span aria-hidden="true">{filters.dir === "asc" ? " ↑" : " ↓"}</span> : null}
      </Link>
    </th>
  );
}

function SkillLine({ skills }: { skills: string[] }) {
  if (skills.length === 0) {
    return null;
  }
  const visible = skills.slice(0, 3);
  const rest = skills.slice(3);
  return (
    <p className="mt-1 text-xs leading-5 text-muted-foreground">
      <span className="sr-only">Skills: </span>
      {visible.join(", ")}
      {rest.length > 0 ? ` +${rest.length}` : ""}
      {rest.length > 0 ? <span className="sr-only">, {rest.join(", ")}</span> : null}
    </p>
  );
}

function RoleDetails({ posting }: { posting: Posting }) {
  return (
    <>
      <ExternalLink href={posting.url}>{posting.title}</ExternalLink>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">{posting.location}</p>
      {posting.salary_text !== null ? (
        <p className="mt-1 text-xs leading-5">Pay {posting.salary_text}</p>
      ) : null}
      <SkillLine skills={posting.skills} />
    </>
  );
}

function Dates({ posting }: { posting: Posting }) {
  return (
    <>
      <p>Seen {formatIsoDate(posting.first_seen)}</p>
      {posting.posted_at !== null ? (
        <p className="text-xs leading-5 text-muted-foreground">Posted {formatIsoDate(posting.posted_at)}</p>
      ) : null}
    </>
  );
}

export function PostingsTable({ rows, filters }: { rows: Posting[]; filters: PostingFilters }) {
  return (
    <>
      <ol className="flex flex-col gap-3 md:hidden">
        {rows.map((posting) => {
          const source = SOURCE_META[posting.source];
          return (
            <li key={posting.id} className="rounded-lg bg-muted/50 px-4 py-3">
              <RoleDetails posting={posting} />
              <p className="mt-2 text-sm">{posting.company}</p>
              <p className="mt-2 flex flex-wrap gap-2">
                <Badge variant="outline">{WORKPLACE_LABELS[posting.workplace]}</Badge>
                <Badge variant="outline">{SENIORITY_LABELS[posting.seniority]}</Badge>
              </p>
              <div className="mt-2 text-sm">
                <Dates posting={posting} />
              </div>
              <p className="mt-2 text-sm">
                Source <ExternalLink href={source.href}>{source.name}</ExternalLink>
              </p>
            </li>
          );
        })}
      </ol>
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[760px] border-collapse text-left text-sm">
          <caption className="sr-only">
            Filtered software postings. The role title opens the original posting. The source opens the board.
          </caption>
          <thead className="border-b border-border text-foreground">
            <tr>
              <SortHeader label="Role" sortKey="title" filters={filters} />
              <SortHeader label="Company" sortKey="company" filters={filters} />
              <SortHeader label="Workplace" sortKey="workplace" filters={filters} />
              <SortHeader label="Seniority" sortKey="seniority" filters={filters} />
              <SortHeader label="Seen" sortKey="first_seen" filters={filters} />
              <SortHeader label="Source" sortKey="source" filters={filters} />
            </tr>
          </thead>
          <tbody>
            {rows.map((posting) => {
              const source = SOURCE_META[posting.source];
              return (
                <tr key={posting.id} className="border-b border-border/80 align-top last:border-b-0">
                  <td className="max-w-sm px-3 py-3">
                    <RoleDetails posting={posting} />
                  </td>
                  <td className="px-3 py-3">{posting.company}</td>
                  <td className="px-3 py-3 whitespace-nowrap">{WORKPLACE_LABELS[posting.workplace]}</td>
                  <td className="px-3 py-3 whitespace-nowrap">{SENIORITY_LABELS[posting.seniority]}</td>
                  <td className="px-3 py-3 whitespace-nowrap">
                    <Dates posting={posting} />
                  </td>
                  <td className="px-3 py-3 whitespace-nowrap">
                    <ExternalLink href={source.href}>{source.name}</ExternalLink>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
