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
- GitHub Actions start on Day 2.

## Day 2 — Storage and daily automation (done)

The fetch still writes one snapshot per UTC date. A second run of the same date refreshes that date's three files and leaves every other date on disk.

The cross-day catalog is `data/jobradar.sqlite`, dumped for review to `data/catalog/postings.json`. The same canonical URL, or the same company and title, is one row. `first_seen` stays on the earliest snapshot. A repost updates `last_seen`. Every fetch rebuilds the catalog from the snapshot files, so a role that leaves those files drops out. When the rebuilt dump matches what is already stored, the database file is left untouched. `days.new` in the catalog is the trend count; `days.seen_again` is the reposts that are kept out of that count. Deleting the sqlite file and running `uv run jobradar fetch` rebuilds it from the snapshot files.

`.github/workflows/daily-fetch.yml` runs at 06:15 UTC and on `workflow_dispatch`. It runs pytest, then `jobradar fetch`, then commits `data/` onto `automation/daily-snapshots` and opens a pull request. It does not push `main`. Actions are pinned to full commit SHAs. Permissions are `contents: read` at the workflow, and `contents: write` plus `pull-requests: write` on the job. There is no cache scope and no repository secret. The sources do not need keys. `GITHUB_TOKEN` is used only to push the data branch and open the pull request. The push is refused if the destination is `main` or `master`, and the script does not force-push.

Retention: keep every daily file in git. Raw snapshots already drop descriptions and logos, and the catalog grows by newly seen roles rather than by reposts. Revisit if `data/` gets large. The workflow is inactive until this branch is merged to `main`, because `schedule` uses the workflow file on the default branch.

## Day 3 — Skill, seniority, and remote extraction (done)

Keyword extraction lives in `pipeline/src/jobradar/extract.py`. The lists it matches are JSON, not code: `taxonomy/skills.json` (aliases such as `js` → JavaScript and `k8s` → Kubernetes), `taxonomy/seniority.json`, and `taxonomy/regions.json`.

`Go`, `R`, and `C` use a Unicode letter boundary and, for those three, refuse `+`, `#`, and `-`. That keeps `Go` out of "go to the office" and `Google`, `R` out of `Rémunération` and `R&D`, and `C` out of `C++` and `C#`. A description or a tag list that names more than 12 skills is treated as a catalog of other roles (Remote OK and some Remotive posts do this) and does not add skills. The title still counts.

Seniority is read from the title and tags only, highest explicit level wins, and `junior_friendly` is true for `intern` and `junior`. A description that says "mentor junior engineers" does not relabel a senior role. Workplace is `remote`, `hybrid`, `onsite`, or `unknown`. The Day 1 `remote` boolean is unchanged. Region limits come from the title, the location, and restriction phrases ("must be located in", "US only"). A marketing line such as "companies in the US and Europe" is not a restriction.

The Day 1 keys are unchanged and still come first. Each posting now also has `seniority`, `skills`, `workplace`, `junior_friendly`, and `regions`. Older snapshot rows omit those keys; `jobradar extract` fills them from the stored title, tags, and location and does not overwrite a row that already has them. The SQLite catalog is schema version 2: opening a version 1 file adds the columns with defaults, and opening that file again does not rewrite it. Re-running the same snapshots does not rewrite the database.

`uv run jobradar fetch` extracts while it normalizes. `uv run jobradar summary` prints workplace, seniority, and top skills beside the Day 1 counts. The deduped aggregate for the dashboard is `data/catalog/trends.json` (top skills, seniority counts, workplace counts, junior-friendly count, regions).

An optional LLM pass runs only when `JOBRADAR_LLM_URL` is set. `JOBRADAR_LLM_API_KEY` and `JOBRADAR_LLM_MODEL` are optional. A missing URL, a failed call, or a response that is not usable JSON keeps the keyword result. Skills and regions from the model are kept only when they are already in the taxonomy. No key is required to run the pipeline, and none is stored in the repo.

The 2026-11-12 fetch, after this extractor, reported 93 software postings and a catalog of 223 unique rows: 16 junior-friendly, workplace 55 remote / 17 hybrid / 150 onsite / 1 unknown. These boards are still senior-heavy (74 senior, 8 junior, 8 intern). Top catalog skills started with AI, Security, Backend, Python, and Full-Stack. Negation is not understood ("Java is not required" still counts Java). Historical snapshots have no description text, so their skills come from the title and tags.

## Day 4 — Dashboard overview (done)

`web/` is a Next.js App Router app (TypeScript, Tailwind, shadcn/ui, Recharts). It does not call the job boards and it has no environment variables. `web/lib/catalog/load.ts` reads `data/catalog/trends.json` and `data/catalog/postings.json` while the page is built, checks that the two files describe the same catalog, and caches that result with `use cache`.

The overview page shows:

- Unique postings, the junior-friendly share (intern + junior), and the fully remote share (`workplace.remote`, hybrid kept separate).
- New postings per snapshot day, from `days.new`. Seen-again counts stay in the chart tooltip.
- Seniority and workplace breakdowns.
- Top skills from `trends.json`.

Run it from `web/` with `npm install`, then `npm run dev`. `npm run lint` and `npm run build` both have to pass. The footer names Remotive, Remote OK, and Arbeitnow. Filters, the postings table, per-posting links, salary-mention rate, and empty-state polish are Day 5. There is no dashboard workflow yet (Day 6) and no deploy (Day 7).

## Day 5 — Filters, postings, and polish

- Filters for source, workplace, seniority, and a date range, applied to the catalog the overview already loads.
- A table of postings with the original URL on each row.
- Empty, loading, and single-source-failed states.
- Salary-mention rate beside the other overview figures.
- Keep the source credits, and link each displayed job back to the board.

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
| `seniority` | string | `intern`, `junior`, `mid`, `senior`, `lead`, `staff`, `principal`, `manager`, or `unknown` |
| `skills` | string[] | Canonical names from the taxonomy. Aliases are folded (`js` → JavaScript) |
| `workplace` | string | `remote`, `hybrid`, `onsite`, or `unknown`. Does not replace `remote` |
| `junior_friendly` | boolean | True when seniority is `intern` or `junior` |
| `regions` | string[] | Country or macro-region limits when the title, location, or a restriction phrase says so |

Later days may add keys. Do not rename or drop these.
