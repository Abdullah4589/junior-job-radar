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

Run it from `web/` with `npm install`, then `npm run dev`. `npm run lint`, `npm run typecheck`, and `npm run build` have to pass. The footer names Remotive, Remote OK, and Arbeitnow. There is no dashboard workflow yet (Day 6) and no deploy (Day 7).

## Day 5 — Filters, postings, and polish (done)

The overview still reads `data/catalog/trends.json` and `data/catalog/postings.json` at build time. Below the charts, the page lists every posting in that catalog.

Filters are seniority, workplace, skill, source, a first-seen date range, text search (title, company, location, skills, tags, and salary text), and junior-friendly only. The table sorts by first seen, posted date, title, company, source, seniority, or workplace, and shows 20 rows at a time. The role title links to the original posting. The source links to that board. Filter, sort, and page live in the query string (`q`, `seniority`, `workplace`, `skill`, `junior`, `source`, `from`, `to`, `sort`, `dir`, `page`), so a view can be shared. Unknown values are dropped, and the page redirects to the canonical query.

The postings block sits in a Suspense boundary. Changing the query shows a loading state while the overview stays put. No matches show an empty state and a way to clear the filters. An inverted date range says so instead of pretending the catalog is empty.

The latest file in `data/raw/` records whether each board responded. The catalog still keeps earlier rows when a board fails, so that status is not on `postings.json`. If one board failed and another succeeded, the page says so. If every board failed, it says the table is the catalog saved before that run. A checkout with no raw snapshot still renders the catalog.

The overview adds a salary-mention rate next to the other headline figures: how many rows have `salary_text`. The Arbeitnow public feed has no pay field, so the rate undercounts.

`npm test` in `web/` runs the filter and source-status unit tests. Day 6 adds Playwright and CI. Day 7 deploys.

## Day 6 — Tests and CI (done)

Playwright covers the dashboard against a production build of the committed catalog. Day 6 served that build with `next start`. Day 7 serves the static export instead, under the GitHub Pages base path. The browser is Chromium. The tests check the overview figures and the four charts, each filter (seniority, workplace, skill, source, first-seen dates, text search, and junior-friendly only) against the table and the query string, pagination, sort, both empty states, and the mobile card list. A request to Remotive, Remote OK, or Arbeitnow fails the test. Run them from `web/` with `npx playwright install chromium` and `npm run e2e`.

`.github/workflows/ci.yml` runs on pull requests and on pushes to `main`. One job runs `uv run pytest`. The other runs `npm ci`, lint, typecheck, `npm test`, `npm run build`, and Playwright. Actions are pinned to full commit SHAs. The workflow permission is `contents: read`. Concurrency cancels an older run on the same ref. npm, uv, and the Playwright browsers are cached. The HTML report is uploaded only when the dashboard job fails.

Extraction did not change, so the parser tests were not rewritten. No test was skipped or weakened.

The daily snapshot workflow failed on 12, 13, and 14 November 2026 for one reason. Pytest passed, `jobradar fetch` wrote that day's snapshot, and the push to `automation/daily-snapshots` succeeded. `gh pr create` then returned `GitHub Actions is not permitted to create or approve pull requests`. The job already has `pull-requests: write`, and the run log shows that scope on the token. Opening a pull request also needs the repository setting **Allow GitHub Actions to create and approve pull requests** (Settings → Actions → General → Workflow permissions). That checkbox is off by default on a personal repository. This change does not add a token or another permission to get around it. The publish script names the setting when GitHub refuses. The commits are already on `automation/daily-snapshots`. The next run after the checkbox is saved opens the pull request. The runs are [2026-11-12](https://github.com/Abdullah4589/junior-job-radar/actions/runs/43245801320), [2026-11-13](https://github.com/Abdullah4589/junior-job-radar/actions/runs/43444201351), and [2026-11-14](https://github.com/Abdullah4589/junior-job-radar/actions/runs/43600151221).

## Day 7 — Deploy and polish (done)

The dashboard is a static export. `web/next.config.ts` sets `output: 'export'`, `basePath` and `assetPrefix` to `/junior-job-radar`, and `trailingSlash`. `npm run build` writes `web/out`. Cache Components stayed off: Next.js refuses Partial Prerendering in export mode (`PPR cannot be enabled in export mode`). The catalog is read once, from the committed `data/catalog` files, while the page is built. Nothing in the repo is a secret, and the site calls no API.

GitHub Pages can host that folder. The page does not need a server. Filters, sort, and pagination read the query string in the browser and replace a dirty query with the canonical one. The static HTML already contains the unfiltered table.

`.github/workflows/pages.yml` runs on a push to `main` and on `workflow_dispatch`. Both jobs run only when the ref is `main`, so a manual run from another branch cannot replace the live site. The build job checks out the commit, runs `npm ci` and `npm run build`, and uploads `web/out` with `actions/upload-pages-artifact`. The deploy job runs `actions/deploy-pages`. Actions are pinned to full commit SHAs. The workflow permission is `contents: read`. The deploy job replaces that with `pages: write` and `id-token: write` only. There is no `contents: write`, no pull-request scope, and no secret. Uploading the artifact uses the Actions runtime token.

The site is `https://abdullah4589.github.io/junior-job-radar/` after the owner sets **Settings → Pages → Build and deployment → Source** to **GitHub Actions**. This change does not flip that setting. Until it is saved, the deploy job cannot publish, and a failed deploy leaves any previous site in place.

A merged data pull request is a push to `main`, so the Pages workflow rebuilds the dashboard from the new catalog. The daily fetch workflow still does not push `main` and was not changed.

Rollback:

- Actions → Pages → open the last good run on `main` → **Re-run all jobs**. The re-run checks out that commit and publishes it again.
- Or revert the merge commit on `main` (a revert pull request is enough). The push to `main` builds the reverted tree and deploys it.
- To take the site offline: **Settings → Pages → Unpublish site**.

Playwright still drives Chromium against the production build. It now loads `http://127.0.0.1:3000/junior-job-radar/` from `web/out`, and one test asserts the base path and that `/_next` assets are not double-prefixed. Screenshots of that build are in `docs/screenshots/` and in the README. The README also states the source bias: these boards are remote-heavy and senior-heavy, Remotive is delayed about 24 hours, Remote OK tags are noisy, and salary coverage is incomplete.

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
