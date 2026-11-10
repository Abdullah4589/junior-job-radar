# Junior Job Radar — 7-day roadmap

Public portfolio project for Abdullah, a fresh software-engineering graduate in Karachi. The product is a daily pipeline of public junior and remote software job postings, plus a dashboard of market trends (skills, remote vs on-site, junior share, salary mentions).

No paid APIs, no API keys, no cloud bills. Each day should leave the repo in a state the next day can build on.

## Day 1 — Repo structure and ingestion (this run)

Python 3.12 pipeline managed with `uv`, under `pipeline/`, so `web/` can land later without a rewrite.

- Fetch at least two free, no-key public sources. Day 1 uses Remotive, Remote OK, and Arbeitnow.
- Normalize every posting into one schema: `id`, `source`, `title`, `company`, `location`, `remote`, `tags`, `salary_text`, `posted_at`, `url`, `fetched_at`.
- Dedupe within the run, then write a dated snapshot:
  - `data/raw/YYYY-MM-DD.json` (compact source payloads; descriptions and logos omitted)
  - `data/normalized/YYYY-MM-DD.json`
  - `data/normalized/YYYY-MM-DD.csv`
- CLI: `uv run jobradar fetch` and `uv run jobradar summary`.
- Summary prints counts per source, top 15 tags, remote share, and how many titles look junior or entry-level.
- Timeouts, retries, a proper User-Agent, and continue if one source fails.
- Pytest coverage for the normalizer and the small helpers it depends on.
- No GitHub Actions yet.

## Day 2 — Storage and daily automation

- Scheduled GitHub Action (cron) that runs the fetch once a day.
- Append that day's snapshot; do not overwrite history.
- Dedupe across days (same canonical URL, or same company + title) so the trend series is not inflated by reposts.
- Keep credentials out of the workflow. The sources used here do not need keys.
- Document the retention choice (keep every daily file in git for now; revisit if the repo grows).

## Day 3 — Skill, seniority, and remote extraction

- Replace the Day 1 title-keyword hints with an explicit extractor module.
- Keyword baseline first: skills, seniority (junior / mid / senior), and remote / hybrid / on-site.
- Optional free LLM structured extraction behind an environment variable. If no key or the call fails, fall back to the keyword result. The pipeline must still run with zero secrets.
- Preserve the Day 1 schema and add fields rather than renaming existing ones (`seniority`, `skills`, `workplace`).
- Unit-test the extractor against saved fixtures, including source failures and empty salary text.

## Day 4–5 — Next.js dashboard

- New `web/` app (App Router, TypeScript). Read the normalized snapshots; do not call job APIs from the browser.
- Charts for top skills, remote vs on-site, junior share, and salary-mention rate.
- Filters for source, remote, seniority, and a date range.
- Empty, loading, and single-source-failed states.
- Credit Remote OK, Remotive, and Arbeitnow on the page, with direct links back to the original postings.

## Day 6 — Tests and CI

- Extend parser unit tests as extraction grows.
- Playwright end-to-end test for the dashboard filters and at least one chart.
- GitHub Actions CI: `uv run pytest` for the pipeline, plus the web typecheck, lint, and Playwright job.
- Do not weaken or delete a test to go green.

## Day 7 — Deploy and polish

- Deploy the dashboard on a free tier (Vercel or Cloudflare).
- README: what the project is, how to run it, screenshots, methodology, and limitations.
- Call out source bias (these boards are remote-heavy and senior-heavy), the 24-hour Remotive delay, noisy Remote OK tags, and that salary coverage is incomplete.
- No production secrets in the repo.

## Schema contract

Normalized records use these keys, in this order:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | `{source}:{native id}` |
| `source` | string | `remotive`, `remoteok`, or `arbeitnow` |
| `title` | string | As published |
| `company` | string | `Unknown` if the source omitted it |
| `location` | string | `Remote` when the board is remote-only and the location is blank |
| `remote` | boolean | Remote OK and Remotive postings are remote |
| `tags` | string[] | Lowercased. Remote OK tags are kept only when the title supports them |
| `salary_text` | string or null | Source text or a formatted min/max. Never invented |
| `posted_at` | string or null | UTC `YYYY-MM-DDTHH:MM:SSZ` |
| `url` | string | Original posting URL. Link here when displaying a job |
| `fetched_at` | string | UTC timestamp for the run |

Later days may add keys. Do not rename or drop these.
