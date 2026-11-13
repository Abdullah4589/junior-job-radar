import { redirect } from "next/navigation";

import { ActiveFilters } from "@/components/postings/active-filters";
import { PostingFilters } from "@/components/postings/posting-filters";
import { PostingsEmpty } from "@/components/postings/postings-empty";
import { PostingsPagination } from "@/components/postings/postings-pagination";
import { PostingsTable } from "@/components/postings/postings-table";
import { SourceNotice } from "@/components/postings/source-notice";
import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import {
  dateBounds,
  filtersToSearchParams,
  parsePostingFilters,
  queryPostings,
  recognizedSearch,
  skillChoices,
  type SearchParamInput,
} from "@/lib/catalog/filters";
import { loadCatalog, loadLatestSourceRun } from "@/lib/catalog/load";
import { formatCount } from "@/lib/catalog/overview";

function resultSummary(matched: number, total: number, start: number, end: number, filtered: boolean): string {
  if (matched === 0) {
    return filtered ? "No postings match these filters." : "No postings are in the catalog yet.";
  }
  const noun = matched === 1 ? "posting" : "postings";
  const shown = `Showing ${formatCount(start)}–${formatCount(end)} of ${formatCount(matched)} ${noun}`;
  if (!filtered || matched === total) {
    return `${shown}.`;
  }
  return `${shown}, from ${formatCount(total)} in the catalog.`;
}

export async function PostingsSection({
  searchParams,
}: {
  searchParams: Promise<SearchParamInput>;
}) {
  const params = await searchParams;
  const [{ catalog }, sourceRun] = await Promise.all([loadCatalog(), loadLatestSourceRun()]);
  const parsed = parsePostingFilters(params);
  const result = queryPostings(catalog.postings, parsed);
  const canonical = filtersToSearchParams(result.filters).toString();
  if (recognizedSearch(params) !== canonical) {
    redirect(canonical.length > 0 ? `/?${canonical}` : "/");
  }

  const bounds = dateBounds(catalog.postings);
  const summary =
    result.notice === "inverted-range"
      ? "The start date is after the end date."
      : resultSummary(result.matched, result.total, result.rangeStart, result.rangeEnd, result.filtered);
  const showRows = result.notice === null && result.rows.length > 0;

  return (
    <section id="postings" aria-labelledby="postings-heading" className="scroll-mt-6">
      <Card>
        <CardHeader>
          <h2 id="postings-heading" className="font-heading text-lg leading-snug font-medium tracking-tight">
            Postings
          </h2>
          <CardDescription className="max-w-2xl text-sm leading-6">
            Every role in the committed catalog. The title opens the original posting, and the source
            opens the board. Choose filters, then apply. The query string is the whole view.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <SourceNotice run={sourceRun} />
          <PostingFilters
            key={canonical}
            filters={result.filters}
            skills={skillChoices(catalog.postings)}
            dateMin={bounds.min}
            dateMax={bounds.max}
            rangeError={result.notice === "inverted-range"}
          />
          <ActiveFilters filters={result.filters} />
          <p aria-live="polite" className="text-sm text-muted-foreground">
            {summary}
          </p>
          {showRows ? (
            <>
              <PostingsTable rows={result.rows} filters={result.filters} />
              <PostingsPagination filters={result.filters} page={result.page} pageCount={result.pageCount} />
            </>
          ) : (
            <PostingsEmpty filtered={result.filtered} inverted={result.notice === "inverted-range"} />
          )}
        </CardContent>
      </Card>
    </section>
  );
}
