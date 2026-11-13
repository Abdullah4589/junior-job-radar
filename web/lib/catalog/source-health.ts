import { SOURCE_META } from "./labels";
import { SOURCES, type Source } from "./types";

export type SourceAttempt = {
  source: Source;
  name: string;
  ok: boolean;
  error: string | null;
};

export type SourceRun = {
  date: string;
  attempts: SourceAttempt[];
};

const ERROR_LIMIT = 160;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function clipError(error: string): string {
  const compact = error.trim().replace(/\s+/g, " ");
  if (compact.length <= ERROR_LIMIT) {
    return compact;
  }
  return `${compact.slice(0, ERROR_LIMIT - 1)}…`;
}

/**
 * Read the `sources` status off a raw snapshot. Records are ignored.
 * Returns null when the document is not a snapshot the dashboard understands.
 */
export function parseSourceRun(value: unknown, date: string): SourceRun | null {
  if (!isRecord(value) || !Array.isArray(value.sources)) {
    return null;
  }
  const attempts: SourceAttempt[] = [];
  for (const item of value.sources) {
    if (!isRecord(item) || typeof item.ok !== "boolean") {
      continue;
    }
    if (typeof item.source !== "string" || !SOURCES.includes(item.source as Source)) {
      continue;
    }
    const source = item.source as Source;
    const error =
      !item.ok && typeof item.error === "string" && item.error.trim().length > 0
        ? clipError(item.error)
        : null;
    attempts.push({
      source,
      name: SOURCE_META[source].name,
      ok: item.ok,
      error,
    });
  }
  if (attempts.length === 0) {
    return null;
  }
  return { date, attempts };
}

/** Known boards that failed, plus any known board missing from the snapshot. */
export function failedAttempts(run: SourceRun): SourceAttempt[] {
  const seen = new Set(run.attempts.map((attempt) => attempt.source));
  const failed = run.attempts.filter((attempt) => !attempt.ok);
  const missing = SOURCES.filter((source) => !seen.has(source)).map(
    (source): SourceAttempt => ({
      source,
      name: SOURCE_META[source].name,
      ok: false,
      error: null,
    }),
  );
  return [...failed, ...missing];
}

export function joinNames(names: readonly string[]): string {
  if (names.length === 0) {
    return "";
  }
  if (names.length === 1) {
    return names[0] ?? "";
  }
  if (names.length === 2) {
    return `${names[0]} and ${names[1]}`;
  }
  return `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
}
