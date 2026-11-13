import Link from "next/link";

import { textLinkClass } from "@/components/text-link";
import { filtersHref, pageWindow, type PostingFilters } from "@/lib/catalog/filters";

function PageLink({
  href,
  children,
  current = false,
}: {
  href?: string;
  children: string;
  current?: boolean;
}) {
  if (current) {
    return (
      <span aria-current="page" className="inline-flex h-11 min-w-11 items-center justify-center rounded-lg bg-primary px-3 text-sm font-medium text-primary-foreground">
        {children}
      </span>
    );
  }
  if (!href) {
    return (
      <span className="inline-flex h-11 items-center px-3 text-sm text-muted-foreground">
        {children}
      </span>
    );
  }
  return (
    <Link href={href} scroll={false} className={`${textLinkClass} inline-flex h-11 items-center px-3 text-sm`}>
      {children}
    </Link>
  );
}

export function PostingsPagination({
  filters,
  page,
  pageCount,
}: {
  filters: PostingFilters;
  page: number;
  pageCount: number;
}) {
  if (pageCount <= 1) {
    return null;
  }
  const window = pageWindow(page, pageCount);

  return (
    <nav aria-label="Postings pages" className="flex flex-wrap items-center gap-1">
      <PageLink href={page > 1 ? filtersHref(filters, { page: page - 1 }) : undefined}>Previous</PageLink>
      {window.map((item, index) =>
        item === "gap" ? (
          <span key={`gap-${index}`} aria-hidden="true" className="px-1 text-muted-foreground">
            …
          </span>
        ) : (
          <PageLink key={item} href={item === page ? undefined : filtersHref(filters, { page: item })} current={item === page}>
            {String(item)}
          </PageLink>
        ),
      )}
      <PageLink href={page < pageCount ? filtersHref(filters, { page: page + 1 }) : undefined}>Next</PageLink>
    </nav>
  );
}
