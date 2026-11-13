import Link from "next/link";

import { focusRingClass } from "@/components/text-link";
import { filterChips, type PostingFilters } from "@/lib/catalog/filters";

export function ActiveFilters({ filters }: { filters: PostingFilters }) {
  const chips = filterChips(filters);
  if (chips.length === 0) {
    return null;
  }

  return (
    <ul aria-label="Active filters" className="flex flex-wrap gap-2">
      {chips.map((chip) => (
        <li key={chip.id}>
          <Link
            href={chip.href}
            scroll={false}
            className={`${focusRingClass} inline-flex min-h-11 items-center gap-2 rounded-full border border-border bg-background px-3 text-sm hover:bg-muted`}
          >
            {chip.label}
            <span className="sr-only">, remove filter</span>
            <span aria-hidden="true">×</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
