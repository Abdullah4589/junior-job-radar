import { Suspense } from "react";

import { PostingsExplorer } from "@/components/postings/postings-explorer";
import { PostingsView } from "@/components/postings/postings-view";
import { loadCatalog, loadLatestSourceRun } from "@/lib/catalog/load";

/**
 * Catalog files are read while the page is built. The fallback is the
 * unfiltered table, so the static HTML already contains it. The explorer
 * replaces that fallback when the query string says something else.
 */
export async function PostingsSection() {
  const [{ catalog }, sourceRun] = await Promise.all([loadCatalog(), loadLatestSourceRun()]);
  return (
    <Suspense fallback={<PostingsView catalog={catalog} sourceRun={sourceRun} params={{}} />}>
      <PostingsExplorer catalog={catalog} sourceRun={sourceRun} />
    </Suspense>
  );
}
