import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "cn";

export function PostingsEmpty({
  filtered,
  inverted,
}: {
  filtered: boolean;
  inverted: boolean;
}) {
  return (
    <div className="rounded-lg border border-dashed border-border px-4 py-10 text-center">
      {inverted ? (
        <p id="date-range-error" role="alert" className="text-sm leading-6">
          The start date is after the end date. Swap the dates, or clear the filters.
        </p>
      ) : null}
      {inverted ? null : (
        <p className="text-sm leading-6">
          {filtered
            ? "No postings match these filters."
            : "No postings are in the catalog yet. The next fetch adds them."}
        </p>
      )}
      {filtered ? (
        <Link href="/" scroll={false} className={cn(buttonVariants({ variant: "outline", className: "mt-4 h-11 px-4" }))}>
          Clear filters
        </Link>
      ) : null}
    </div>
  );
}
