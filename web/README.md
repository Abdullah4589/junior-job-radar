# Dashboard

Next.js dashboard for Junior Job Radar. The page reads `../data/catalog/trends.json` and `../data/catalog/postings.json` when it is built. The latest `../data/raw/YYYY-MM-DD.json` supplies the per-board success flag for the source notice. There are no job-board requests and no environment variables.

The overview (counts, new postings, seniority, workplace, top skills, salary-mention rate) is the top of the page. Filters and a sortable, paginated postings table sit below it. Filter state is the query string: `q`, `seniority`, `workplace`, `skill`, `junior`, `source`, `from`, `to`, `sort`, `dir`, and `page`. The role title opens the original posting. The source opens the board.

```powershell
npm install
npm run dev
npm test
npm run lint
npm run typecheck
npm run build
```

See [docs/ROADMAP.md](../docs/ROADMAP.md).
