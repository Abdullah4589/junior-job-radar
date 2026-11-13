import { Suspense } from "react";

import { ChartSection } from "@/components/overview/chart-section";
import { BreakdownChart } from "@/components/overview/breakdown-chart";
import { KpiStrip } from "@/components/overview/kpi-strip";
import { NewPostingsChart } from "@/components/overview/new-postings-chart";
import { SkillsChart } from "@/components/overview/skills-chart";
import { PostingsSection } from "@/components/postings/postings-section";
import { PostingsSkeleton } from "@/components/postings/postings-skeleton";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { loadOverview } from "@/lib/catalog/load";
import { formatCount } from "@/lib/catalog/overview";

export default async function HomePage({ searchParams }: PageProps<"/">) {
  const overview = await loadOverview();
  const total = formatCount(overview.totalPostings);

  return (
    <>
      <SiteHeader snapshotLabel={overview.snapshotLabel} />
      <main id="content" tabIndex={-1} className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-4 py-8 outline-none sm:px-6">
        <KpiStrip overview={overview} />
        <ChartSection
          id="new-postings"
          title="New postings"
          description={`Roles first seen on that snapshot day, across ${total} unique postings. The tooltip also shows how many were seen again.`}
          table={{
            caption: "New postings per snapshot day",
            headers: ["Date", "New", "Seen again", "Collected"],
            rows: overview.days.map((day) => [
              day.date,
              String(day.new),
              String(day.seenAgain),
              String(day.collected),
            ]),
          }}
        >
          <NewPostingsChart days={overview.days} />
        </ChartSection>
        <div className="grid items-start gap-6 lg:grid-cols-2">
          <ChartSection
            id="seniority"
            title="Seniority"
            description="Highest explicit level in the title or tags. Unspecified means the title and tags never named a level."
            table={{
              caption: "Postings by seniority",
              headers: ["Seniority", "Postings", "Share"],
              rows: overview.seniority.map((row) => [row.label, String(row.count), row.shareLabel]),
            }}
          >
            <BreakdownChart rows={overview.seniority} label="Postings by seniority" />
          </ChartSection>
          <ChartSection
            id="workplace"
            title="Workplace"
            description="Remote, hybrid, or on-site from the title, the location, and the board's remote flag. The remote share above is the fully remote slice."
            table={{
              caption: "Postings by workplace",
              headers: ["Workplace", "Postings", "Share"],
              rows: overview.workplace.map((row) => [row.label, String(row.count), row.shareLabel]),
            }}
          >
            <BreakdownChart rows={overview.workplace} label="Postings by workplace" colorByKey />
          </ChartSection>
        </div>
        <ChartSection
          id="top-skills"
          title="Top skills"
          description={`Canonical skill names from the taxonomy. A posting can carry more than one, so each share is of ${total} roles.`}
          table={{
            caption: "Top skills in the catalog",
            headers: ["Skill", "Postings", "Share"],
            rows: overview.skills.map((row) => [row.skill, String(row.count), row.shareLabel]),
          }}
        >
          <SkillsChart skills={overview.skills} />
        </ChartSection>
        <Suspense fallback={<PostingsSkeleton />}>
          <PostingsSection searchParams={searchParams} />
        </Suspense>
      </main>
      <SiteFooter />
    </>
  );
}
