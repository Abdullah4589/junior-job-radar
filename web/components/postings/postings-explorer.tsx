"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { PostingsView } from "@/components/postings/postings-view";
import {
  filtersToSearchParams,
  inputFromSearchParams,
  parsePostingFilters,
  queryPostings,
  recognizedSearch,
} from "@/lib/catalog/filters";
import type { SourceRun } from "@/lib/catalog/source-health";
import type { Catalog } from "@/lib/catalog/types";

/**
 * The static export has one HTML file. The query string is applied here, after
 * hydration, and a dirty query is replaced with the canonical one. The same
 * path runs under `next dev`.
 */
export function PostingsExplorer({
  catalog,
  sourceRun,
}: {
  catalog: Catalog;
  sourceRun: SourceRun | null;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const params = inputFromSearchParams(searchParams);
  const recognized = recognizedSearch(params);
  const canonical = filtersToSearchParams(
    queryPostings(catalog.postings, parsePostingFilters(params)).filters,
  ).toString();

  useEffect(() => {
    if (recognized === canonical) {
      return;
    }
    router.replace(canonical.length > 0 ? `/?${canonical}` : "/", { scroll: false });
  }, [canonical, recognized, router]);

  return <PostingsView catalog={catalog} sourceRun={sourceRun} params={params} />;
}
