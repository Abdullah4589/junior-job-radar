import { Card, CardContent, CardDescription, CardHeader } from "@/components/ui/card";
import { formatCount, type Overview } from "@/lib/catalog/overview";

function Kpi({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardDescription className="text-xs font-medium tracking-[0.14em] uppercase">
          {label}
        </CardDescription>
        <p className="font-heading text-4xl tracking-tight tabular-nums">{value}</p>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-6 text-muted-foreground">{detail}</p>
      </CardContent>
    </Card>
  );
}

export function KpiStrip({ overview }: { overview: Overview }) {
  const total = formatCount(overview.totalPostings);
  return (
    <section aria-label="Headline figures">
      <div className="grid gap-4 sm:grid-cols-3">
        <Kpi
          label="Unique postings"
          value={total}
          detail="One row per role. A later repost updates the last-seen date and keeps that row."
        />
        <Kpi
          label="Junior-friendly"
          value={overview.juniorFriendlyShare}
          detail={`${formatCount(overview.juniorFriendlyCount)} of ${total} titles say intern or junior.`}
        />
        <Kpi
          label="Remote"
          value={overview.remoteShare}
          detail={`${formatCount(overview.remoteCount)} of ${total} are fully remote. Hybrid is counted on its own.`}
        />
      </div>
    </section>
  );
}
