# Dashboard

Next.js dashboard for Junior Job Radar. `npm run build` reads `../data/catalog/trends.json` and `../data/catalog/postings.json` and writes a static site to `out/`. The latest `../data/raw/YYYY-MM-DD.json` supplies the per-board success flag. There are no job-board requests and no environment variables.

The production site is served at `/junior-job-radar/` (`basePath` and `assetPrefix` in `next.config.ts`), which is the GitHub Pages project path. `npm run dev` uses the same path.

```powershell
npm install
npm run dev
npm test
npm run lint
npm run typecheck
npm run build
npm run start
npx playwright install chromium
npm run e2e
```

`npm run dev` opens `http://localhost:3000/junior-job-radar/`. `npm run start` serves the static `out/` directory at `http://127.0.0.1:3000/junior-job-radar/`. Run `npm run build` first.

`npm run e2e` runs Playwright against that static export. The tests use the committed catalog and do not call the job boards. Chromium is enough. One test checks that scripts and styles load from `/junior-job-radar/_next/`.

See [docs/ROADMAP.md](../docs/ROADMAP.md) and the [root README](../README.md).
