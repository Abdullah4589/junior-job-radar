import { access, readFile } from "node:fs/promises";
import path from "node:path";

import { cacheLife } from "next/cache";

import { toOverview, type Overview } from "@/lib/catalog/overview";
import { parseCatalog, parseTrends } from "@/lib/catalog/parse";
import type { CatalogBundle } from "@/lib/catalog/types";

/**
 * Read the committed catalog. `npm run dev` and `npm run build` are started
 * from `web/`, so the files live one directory up. A checkout that runs from
 * the repo root is accepted too.
 */
async function catalogDirectory(): Promise<string> {
  const candidates = [
    path.resolve(process.cwd(), "data", "catalog"),
    path.resolve(process.cwd(), "..", "data", "catalog"),
  ];
  for (const dir of candidates) {
    try {
      await access(path.join(dir, "trends.json"));
      await access(path.join(dir, "postings.json"));
      return dir;
    } catch {
      continue;
    }
  }
  throw new Error(
    "Could not find data/catalog. Run the dashboard from web/ so it can read the repo catalog.",
  );
}

async function readJson(filePath: string): Promise<unknown> {
  let text: string;
  try {
    text = await readFile(filePath, "utf8");
  } catch (error) {
    const detail = error instanceof Error ? error.message : "unknown error";
    throw new Error(`Could not read ${filePath}: ${detail}`);
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    throw new Error(`${filePath} is not valid JSON`);
  }
}

async function readCatalog(): Promise<CatalogBundle> {
  const dir = await catalogDirectory();
  const [trendsValue, catalogValue] = await Promise.all([
    readJson(path.join(dir, "trends.json")),
    readJson(path.join(dir, "postings.json")),
  ]);
  return {
    trends: parseTrends(trendsValue),
    catalog: parseCatalog(catalogValue),
  };
}

export async function loadCatalog(): Promise<CatalogBundle> {
  "use cache";
  cacheLife("max");
  return readCatalog();
}

export async function loadOverview(): Promise<Overview> {
  "use cache";
  cacheLife("max");
  const { trends, catalog } = await readCatalog();
  return toOverview(trends, catalog);
}
