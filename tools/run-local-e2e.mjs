import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { extname, join, normalize } from "node:path";
import { spawn } from "node:child_process";

const baseUrl = process.env.DIOPSIDE_E2E_BASE_URL;

if (baseUrl) {
  await checkRemote(baseUrl.replace(/\/$/, ""));
} else {
  await runLocal();
}

async function runLocal() {
  await import("./build-web.mjs");
  const web = await startStaticServer("build/web", 8786);
  const api = spawn("python3", ["-m", "diopside_api.local_server", "--port", "8787"], {
    env: {
      ...process.env,
      PYTHONPATH: "apps/shared/src:apps/api/src",
      DIOPSIDE_PUBLIC_DATA_DIR: "data/fixtures/public",
      DIOPSIDE_LOCAL_FIXTURE_MODE: "true",
      DIOPSIDE_ADMIN_TOKEN: "local-secret",
      DIOPSIDE_ADMIN_CSRF_TOKEN: "local-csrf",
      DIOPSIDE_ALLOW_DRY_RUN_JOBS: "true"
    },
    stdio: ["ignore", "pipe", "pipe"]
  });
  try {
    await waitFor(() => fetch("http://127.0.0.1:8787/api/health").then((r) => r.ok));
    await checkStatic("http://127.0.0.1:8786");
    await checkApi("http://127.0.0.1:8787");
    await checkAdminDryRun("http://127.0.0.1:8787");
    console.log("local e2e passed");
  } finally {
    api.kill();
    await new Promise((resolve) => web.close(resolve));
  }
}

async function checkRemote(url) {
  await checkStatic(url);
  await checkApi(url);
  console.log(`remote e2e passed for ${url}`);
}

async function checkStatic(url) {
  const html = await text(`${url}/`);
  if (!html.includes("diopside")) throw new Error("home html does not include diopside");
  const manifest = await json(`${url}/data/latest-manifest.json`);
  const videos = await json(`${url}${manifest.indexes.videos_latest}`);
  if (!videos.items.length) throw new Error("videos index is empty");
  const detail = await json(`${url}${videos.items[0].detail_path}`);
  if (!detail.video?.youtube_url) throw new Error("video detail missing youtube_url");
}

async function checkApi(url) {
  const health = await json(`${url}/api/health`);
  if (health.service !== "diopside" || health.status !== "ok") throw new Error("health failed");
  const videos = await json(`${url}/api/videos?limit=1`);
  if (!videos.items?.length) throw new Error("api videos empty");
}

async function checkAdminDryRun(url) {
  const created = await json(`${url}/api/admin/jobs/static-export`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      Authorization: "Bearer local-secret",
      "X-CSRF-Token": "local-csrf"
    },
    body: JSON.stringify({ idempotency_key: "local-e2e-static-export", scope: "all" })
  });
  if (created.job_type !== "static_export" || created.derived_state !== "queued") throw new Error("admin static-export dry run failed");
  const jobs = await json(`${url}/api/admin/jobs`, { headers: { Authorization: "Bearer local-secret" } });
  if (!jobs.items?.some((item) => item.job_id === created.job_id)) throw new Error("admin job list missing dry-run job");
  const detail = await json(`${url}/api/admin/jobs/${created.job_id}`, { headers: { Authorization: "Bearer local-secret" } });
  if (!detail.item?.events?.length) throw new Error("admin job detail missing events");
}

async function json(url, options = {}) {
  const res = await fetch(url, options);
  const body = await res.json();
  if (!res.ok) throw new Error(`${url} returned ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function text(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} returned ${res.status}`);
  return res.text();
}

async function startStaticServer(root, port) {
  const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml" };
  const server = createServer(async (req, res) => {
    const pathname = new URL(req.url, `http://127.0.0.1:${port}`).pathname;
    const rel = normalize(pathname === "/" ? "index.html" : pathname.slice(1));
    const file = join(root, rel);
    if (!file.startsWith(root) || !existsSync(file)) {
      res.writeHead(404);
      res.end("not found");
      return;
    }
    res.writeHead(200, { "content-type": types[extname(file)] ?? "application/octet-stream" });
    res.end(await readFile(file));
  });
  await new Promise((resolve) => server.listen(port, "127.0.0.1", resolve));
  return server;
}

async function waitFor(fn) {
  const start = Date.now();
  while (Date.now() - start < 8000) {
    try {
      if (await fn()) return;
    } catch {
      // retry until timeout
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error("timeout waiting for local api");
}
