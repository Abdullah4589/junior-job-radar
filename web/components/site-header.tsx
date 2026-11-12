import { Badge } from "@/components/ui/badge";

function RadarMark() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" aria-hidden="true" className="text-primary">
      <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="18" cy="18" r="10" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="18" cy="18" r="2.5" fill="currentColor" />
      <path d="M18 18 L30 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function SiteHeader({ snapshotLabel }: { snapshotLabel: string }) {
  return (
    <header className="border-b border-border/80">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10 sm:py-14">
        <div className="flex items-center gap-3 text-primary">
          <RadarMark />
          <p className="text-xs font-medium tracking-[0.18em] uppercase">Daily market snapshot</p>
        </div>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl">
            <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">Junior Job Radar</h1>
            <p className="mt-4 text-base leading-7 text-muted-foreground">
              Deduped software roles from the public Remotive, Remote OK, and Arbeitnow feeds.
              Junior-friendly means the title or tags say intern or junior. Remote means the
              workplace extractor called the role fully remote. The trend counts roles first seen
              on that snapshot day.
            </p>
          </div>
          <Badge variant="outline" className="h-7 px-3 text-sm">
            {snapshotLabel}
          </Badge>
        </div>
      </div>
    </header>
  );
}
