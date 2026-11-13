export function PostingsSkeleton() {
  return (
    <section aria-labelledby="postings-loading" aria-busy="true" className="flex flex-col gap-4">
      <h2 id="postings-loading" className="font-heading text-lg leading-snug font-medium tracking-tight">
        Postings
      </h2>
      <p className="text-sm text-muted-foreground">Loading postings…</p>
      <div className="h-56 animate-pulse rounded-xl bg-muted" />
      <div className="h-80 animate-pulse rounded-xl bg-muted" />
    </section>
  );
}
