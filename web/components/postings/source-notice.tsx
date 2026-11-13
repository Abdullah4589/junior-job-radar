import { formatIsoDate } from "@/lib/catalog/format";
import { failedAttempts, joinNames, type SourceRun } from "@/lib/catalog/source-health";
import { SOURCES } from "@/lib/catalog/types";

export function SourceNotice({ run }: { run: SourceRun | null }) {
  if (!run) {
    return null;
  }
  const failed = failedAttempts(run);
  if (failed.length === 0) {
    return null;
  }

  const date = formatIsoDate(run.date);
  const names = joinNames(failed.map((attempt) => attempt.name));
  const allFailed = failed.length >= SOURCES.length;
  const details = failed
    .filter((attempt) => attempt.error)
    .map((attempt) => `${attempt.name}: ${attempt.error}`)
    .join(" ");

  return (
    <div
      role={allFailed ? "alert" : "status"}
      className={
        allFailed
          ? "rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm leading-6 text-foreground"
          : "rounded-lg border border-[oklch(0.72_0.07_75)] bg-[oklch(0.96_0.03_90)] px-4 py-3 text-sm leading-6 text-foreground"
      }
    >
      {allFailed ? (
        <p>None of the boards responded on the {date} snapshot. The table is the catalog saved before that run.</p>
      ) : (
        <p>
          {names} did not respond on the {date} snapshot. Roles collected on earlier days stay in the table.
        </p>
      )}
      {details.length > 0 ? <p className="mt-1 text-muted-foreground">{details}</p> : null}
    </div>
  );
}
