/**
 * Serves `web/out` at /junior-job-radar, which is the GitHub Pages project path.
 * Query strings stay on the client. The file is the preview server and the
 * Playwright server. Keep the path in step with `repositoryBasePath` in
 * `web/next.config.ts`.
 */
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, sep } from "node:path";
import { fileURLToPath } from "node:url";

const repositoryBasePath = "/junior-job-radar";
const outDir = fileURLToPath(new URL("../out", import.meta.url));
const host = process.env.HOST ?? "127.0.0.1";
const port = Number(process.env.PORT ?? "3000");

const TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".map": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function insideOut(candidate) {
  return candidate === outDir || candidate.startsWith(`${outDir}${sep}`);
}

function fileFor(candidate) {
  if (!insideOut(candidate)) {
    return null;
  }
  if (existsSync(candidate) && statSync(candidate).isFile()) {
    return candidate;
  }
  const asHtml = `${candidate}.html`;
  if (existsSync(asHtml) && statSync(asHtml).isFile()) {
    return asHtml;
  }
  const index = join(candidate, "index.html");
  if (insideOut(index) && existsSync(index) && statSync(index).isFile()) {
    return index;
  }
  return null;
}

function resolveRequest(pathname) {
  if (pathname !== repositoryBasePath && !pathname.startsWith(`${repositoryBasePath}/`)) {
    return null;
  }
  let relative = pathname.slice(repositoryBasePath.length).replace(/^\/+/, "");
  try {
    relative = decodeURIComponent(relative);
  } catch {
    return null;
  }
  const normalized = normalize(relative);
  if (normalized === ".." || normalized.startsWith(`..${sep}`) || normalized.includes(`..${sep}`)) {
    return null;
  }
  return fileFor(join(outDir, normalized));
}

if (!existsSync(join(outDir, "index.html"))) {
  console.error("web/out/index.html is missing. From web/, run npm run build first.");
  process.exit(1);
}

const server = createServer((request, response) => {
  const pathname = new URL(request.url ?? "/", "http://127.0.0.1").pathname;
  const file = resolveRequest(pathname);
  if (!file || (request.method !== "GET" && request.method !== "HEAD")) {
    response.writeHead(file ? 405 : 404, { "content-type": "text/plain; charset=utf-8" });
    response.end(file ? "Method not allowed" : "Not found");
    return;
  }
  response.writeHead(200, {
    "content-type": TYPES[extname(file)] ?? "application/octet-stream",
    "cache-control": "no-store",
  });
  if (request.method === "HEAD") {
    response.end();
    return;
  }
  createReadStream(file).pipe(response);
});

server.listen(port, host, () => {
  console.log(`Dashboard at http://${host}:${port}${repositoryBasePath}/`);
});
