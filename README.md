# Junior Job Radar

Daily pipeline and (from Day 4) dashboard that tracks public junior and remote software jobs: which skills show up, how much of the market is remote, how thin the junior slice is, and how often a posting mentions pay.

Built by Abdullah, a software-engineering graduate in Karachi, as a public portfolio project. It uses free job-board APIs only. There is no paid plan and no API key.

Day 1 is the ingestion pipeline. Day 2 stores every posting in a deduped catalog and runs the fetch on a daily schedule. The dashboard and deployment come later. The day-by-day plan is in [docs/ROADMAP.md](docs/ROADMAP.md).

## Roadmap

| Day | Work |
| --- | --- |
| 1 | Python ingestion pipeline, normalized snapshots, `fetch` and `summary` |
| 2 | Deduped SQLite catalog, daily snapshots kept in git, scheduled workflow that opens a pull request (this repo state) |
| 3 | Skill, seniority, and workplace extraction (keywords, then an optional free LLM with a fallback) |
| 4–5 | Next.js dashboard with charts and filters |
| 6 | Parser tests, Playwright, CI |
| 7 | Free-tier deploy and a README with screenshots, methodology, and limitations |

## Run the pipeline

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.12 (uv will fetch 3.12 from the pin in `pipeline/.python-version` if you don't have it).

```powershell
cd pipeline
uv sync
uv run jobradar fetch
uv run jobradar summary
uv run pytest
```

`fetch` writes three files, using today's UTC date:

- `data/raw/YYYY-MM-DD.json` — compact source payloads. Descriptions and logos are left out so the repo stays small.
- `data/normalized/YYYY-MM-DD.json` — deduped software roles
- `data/normalized/YYYY-MM-DD.csv` — the same rows

Running `fetch` again on the same UTC date refreshes that date's three snapshot files. Files for other dates stay as they are. The same run rebuilds the catalog from every snapshot:

- `data/jobradar.sqlite` — one row per posting. The same canonical URL, or the same company and title, does not get a second row.
- `data/catalog/postings.json` — the same rows as text, including `first_seen`, `last_seen`, and `days.new` (the deduped count for each date).

A second fetch that sees the same postings does not add rows and does not rewrite the database. A richer repost (a salary, more tags) can fill in the stored row and keeps `first_seen`. A role that disappears from the snapshot files drops out of the catalog. Deleting `data/jobradar.sqlite` and running `fetch` rebuilds it.

`summary` reads the latest normalized snapshot (or `--date YYYY-MM-DD`) and prints counts per source, the top 15 tags, the remote share, and how many postings look junior or entry-level. That summary is one day's file, including roles that were already in an earlier snapshot. The deduped trend series is `days` in the catalog.

## What gets stored

Every normalized posting has the same fields:

`id`, `source`, `title`, `company`, `location`, `remote`, `tags`, `salary_text`, `posted_at`, `url`, `fetched_at`

A posting is kept when the title (or a Remotive software category, or an Arbeitnow "Software Development" tag) looks like a software role. Sales, nursing, accounting, and similar listings from the same feeds are stored in the raw snapshot and left out of the normalized file.

Duplicates inside one run are collapsed. The same URL matches after tracking parameters are stripped. The same company and title match after punctuation and suffixes like "Inc" or "GmbH" are folded. The record with a salary, more tags, or a posted date wins.

Junior / entry-level in the summary is a keyword check on the title and tags (`junior`, `jr`, `intern`, `entry-level`, `new grad`, `working student`, and a few close phrases). It does not read the job description. Day 3 replaces it with a real extractor.

Tags are lowercased. Skills named in the title (`python`, `react`, `full-stack`, …) are added so the three boards can be compared. Remote OK's API attaches unrelated tags to listings (a nurse role can be tagged `golang`), so a Remote OK tag is kept only when the title also says it. Generic labels (`engineer`, `full time`) and parenthetical team names (`engineering (ads)`) are dropped. The raw snapshot still has the original tag list.

## Daily schedule

`.github/workflows/daily-fetch.yml` runs at 06:15 UTC, and when someone starts it by hand from `main`. It installs the pinned uv toolchain, runs `uv run pytest`, then `uv run jobradar fetch`.

The job commits changes under `data/` onto `automation/daily-snapshots` and opens a pull request into `main`. It does not push `main`. The only credential is the run's `GITHUB_TOKEN`, limited to `contents: write` and `pull-requests: write`. The boards need no API key, and the workflow file has no secrets. Actions are pinned to full commit SHAs. A run with no data change does not create an empty commit. Two runs cannot overlap (`concurrency: daily-snapshot`).

The schedule starts after this workflow is on `main`. Until the data pull request is merged, the next day checks out `automation/daily-snapshots` (so unmerged days stack) and merges `main` into it. A conflict in pipeline code fails the job. A conflict in an older snapshot keeps `main`'s copy, and the fetch rebuilds the catalog from the snapshot files.

## Sources

One request per source per run. If a source times out or returns a bad payload, the run logs the error and continues with the others. Requests use a 20s timeout, up to 3 attempts, and a `JuniorJobRadar` User-Agent.

| Source | Endpoint | Notes |
| --- | --- | --- |
| [Remotive](https://remotive.com) | `https://remotive.com/api/remote-jobs` | Public, delayed about 24 hours. Link the Remotive job URL and mention Remotive. Their docs ask for at most a few calls a day. The free feed currently ignores `category` and `search` and returns a small list. |
| [Remote OK](https://remoteok.com) | `https://remoteok.com/api` | Public JSON. Link each job URL with a normal follow link (not `nofollow`) and mention Remote OK. Their logo is not used. |
| [Arbeitnow](https://www.arbeitnow.com) | `https://www.arbeitnow.com/api/job-board-api` | Free job-board API. Page 1 is the newest 300 posts. Please link back to Arbeitnow. This board is not remote-only, so `remote` comes from the payload. |

Checked and not used: The Muse's old public jobs URL (`https://www.themuse.com/api/public/jobs`) responds with 404, so it is not a source.

Salary text is whatever the board provided. Remote OK's `0` minimum and maximum mean "not stated" and become an empty salary. Arbeitnow's public records do not include a salary field.

## First snapshot (2026-11-10)

`data/` includes the snapshot from the Day 1 run. `uv run jobradar summary` on that file prints:

```text
Junior Job Radar — summary 2026-11-10
snapshot: data/normalized/2026-11-10.json
84 software postings

Counts by source
  arbeitnow  51
  remoteok   28
  remotive   5

Remote share: 39/84 (46.4%)
Junior / entry-level: 3/84 (3.6%)

Top 15 tags
   1. java (8)
   2. backend (7)
   3. full-stack (6)
   4. software development (6)
   5. ai/ml (5)
   6. angular (4)
   7. frontend (4)
   8. software engineering (4)
   9. typescript (4)
  10. .net (3)
  11. c++ (3)
  12. cloud (3)
  13. devops (3)
  14. docker (3)
  15. javascript (3)
```

That junior share is the finding, not a bug in the count: these three boards are mostly senior. Day 3 can read descriptions, but it should not invent junior roles the titles do not claim.

## Limitations

- Remotive's free API currently returns 12 jobs and ignores `category` and `search`. The feed is delayed about 24 hours.
- Remote OK's tag list is not a skill list. Normalized tags only keep a Remote OK tag when the title supports it.
- Arbeitnow's first page is 300 mixed roles, mostly on-site in Europe, with no salary field. Software roles are filtered in by title.
- Junior / entry-level is a keyword check. It misses junior roles whose titles only say "Software Engineer".
- Fetching the same UTC date again refreshes that date's snapshot files. Other dates stay. The catalog keeps one row per posting, so a repost updates `last_seen` and the trend count uses `days.new`.
- No paid APIs and no API keys. The Muse's old public jobs endpoint returned 404 and is not a source.

## Layout

```
pipeline/                         Python 3.12 package (uv)
data/raw/                         One compact payload file per UTC date
data/normalized/                  One JSON and one CSV per UTC date
data/catalog/postings.json        Deduped catalog, one row per posting
data/jobradar.sqlite              Same catalog in SQLite
.github/workflows/daily-fetch.yml Daily fetch. Opens a pull request, does not push main
docs/                             Roadmap for the rest of the week
web/                              Next.js dashboard, added on Day 4
```

## License

MIT. Job text remains the property of the boards and the employers. This project stores titles, companies, tags, and links so the dashboard can cite them.
