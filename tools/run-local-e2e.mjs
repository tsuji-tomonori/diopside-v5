import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { tmpdir } from "node:os";
import { spawn } from "node:child_process";

const baseUrl = process.env.DIOPSIDE_E2E_BASE_URL;

if (baseUrl) {
  await checkRemote(baseUrl.replace(/\/$/, ""));
} else {
  await runLocal();
}

async function runLocal() {
  await import("./build-web.mjs");
  const web = await startStaticServer("build/web", 8786, "http://127.0.0.1:8787");
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
    await checkBrowserFlows("http://127.0.0.1:8786");
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
  const quota = await json(`${url}/api/admin/quota-usage`, { headers: { Authorization: "Bearer local-secret" } });
  if (!Array.isArray(quota.items)) throw new Error("admin quota usage response must include items array");
  for (const item of quota.items) {
    for (const key of ["method", "units", "video_count", "channel_id", "job_id"]) {
      if (!(key in item)) throw new Error(`admin quota usage item missing ${key}`);
    }
  }
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

async function checkBrowserFlows(url) {
  const chrome = await startChrome();
  try {
    const client = await openChromePage(chrome.port, url);
    try {
      await client.send("Page.enable");
      await client.send("Runtime.enable");
      await client.send("Page.navigate", { url });
      await waitFor(async () => {
        const ready = await client.evaluate("document.readyState === 'complete' && document.querySelectorAll('.video-card').length > 0 && !!document.querySelector('#videoDetail .primary-link')");
        return ready === true;
      });
      await client.evaluate(`(async () => {
        const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
        const waitFor = async (fn) => {
          const start = Date.now();
          while (Date.now() - start < 6000) {
            if (fn()) return;
            await wait(100);
          }
          throw new Error("browser flow timeout");
        };
        const text = (selector) => document.querySelector(selector)?.textContent || "";
        const click = (selector) => {
          const node = document.querySelector(selector);
          if (!node) throw new Error("missing selector: " + selector);
          node.click();
        };
        const setInput = (selector, value) => {
          const node = document.querySelector(selector);
          if (!node) throw new Error("missing input: " + selector);
          node.value = value;
          node.dispatchEvent(new Event("input", { bubbles: true }));
          node.dispatchEvent(new Event("change", { bubbles: true }));
        };
        const setSelect = (selector, value) => {
          const node = document.querySelector(selector);
          if (!node) throw new Error("missing select: " + selector);
          node.value = value;
          node.dispatchEvent(new Event("change", { bubbles: true }));
        };

        await waitFor(() => document.querySelector('#videoDetail .wordcloud'));
        if (!document.querySelector('#videoDetail .primary-link[href*="youtube.com"]')) throw new Error("detail youtube link missing");
        if (!document.querySelector('#videoDetail .timestamp-list a[href*="t=120s"]')) throw new Error("timestamp link missing");
        if (!document.querySelector('#videoDetail .wordcloud')) throw new Error("wordcloud missing");

        setInput("#searchInput", "検索");
        await waitFor(() => text("#resultCount").includes("1件") && text("#videoList").includes("検索とタグ確認用アーカイブ"));

        click('#tagFilters button[data-tag="歌枠"]');
        await waitFor(() => text("#resultCount").includes("1件") && text("#videoList").includes("歌枠"));
        click("#videoList .video-main");
        await waitFor(() => text("#videoDetail").includes("検索とタグ確認用アーカイブ") && document.querySelector('#videoDetail .timestamp-list a[href*="t=60s"]'));

        click('[data-action="admin"]');
        await waitFor(() => document.querySelector("#adminPanel").open);
        setInput('#adminJobForm input[name="passphrase"]', "local-secret");
        setSelect('#adminJobForm select[name="jobType"]', "static-export");
        document.querySelector("#adminJobForm").requestSubmit();
        await waitFor(() => text("#adminResult").includes("static_export") && document.querySelector('#adminJobId').value);
        click("#loadJobDetailButton");
        await waitFor(() => text("#adminData").includes("JobEvent") && text("#adminData").includes("queued"));

        setInput('#adminChannelForm input[name="channelId"]', "ch-local-e2e");
        setInput('#adminChannelForm input[name="uploadsPlaylistId"]', "UUlocalE2E");
        setInput('#adminChannelForm input[name="displayName"]', "Local E2E Channel");
        setInput('#adminChannelForm input[name="metadataIntervalMinutes"]', "720");
        setInput('#adminChannelForm input[name="liveScanIntervalMinutes"]', "30");
        document.querySelector('#adminChannelForm input[name="enabled"]').checked = true;
        document.querySelector('#adminChannelForm input[name="notificationEnabled"]').checked = true;
        document.querySelector("#adminChannelForm").requestSubmit();
        await waitFor(() => text("#adminResult").includes("ch-local-e2e") && text("#adminChannelList").includes("Local E2E Channel"))
          .catch(() => {
            throw new Error("channel settings flow failed: " + text("#adminResult") + " | " + text("#adminChannelList"));
          });
        click("#loadChannelsButton");
        await waitFor(() => text("#adminChannelList").includes("UUlocalE2E"));
      })()`);
    } finally {
      client.close();
    }
  } finally {
    await chrome.stop();
  }
}

async function startChrome() {
  const port = 9224;
  const profile = await mkdtemp(join(tmpdir(), "diopside-chrome-"));
  const proc = spawn("google-chrome", [
    "--headless=new",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    `--user-data-dir=${profile}`,
    `--remote-debugging-port=${port}`,
    "about:blank"
  ], { stdio: ["ignore", "ignore", "ignore"] });
  try {
    await waitFor(() => fetch(`http://127.0.0.1:${port}/json/version`).then((res) => res.ok), 15000);
  } catch (error) {
    await stopProcess(proc);
    await removePathWithRetry(profile);
    throw error;
  }
  return {
    port,
    async stop() {
      await stopProcess(proc);
      await removePathWithRetry(profile);
    }
  };
}

async function stopProcess(proc) {
  if (proc.exitCode !== null || proc.signalCode !== null) return;
  proc.kill();
  await new Promise((resolve) => proc.once("exit", resolve));
}

async function removePathWithRetry(path) {
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      await rm(path, { recursive: true, force: true });
      return;
    } catch (error) {
      if (error?.code !== "ENOTEMPTY" && error?.code !== "EBUSY") throw error;
      await new Promise((resolve) => setTimeout(resolve, 200));
    }
  }
  await rm(path, { recursive: true, force: true });
}

async function openChromePage(port, url) {
  const response = await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
  if (!response.ok) throw new Error(`failed to open chrome page: ${response.status}`);
  const target = await response.json();
  return createCdpClient(target.webSocketDebuggerUrl);
}

function createCdpClient(webSocketDebuggerUrl) {
  const socket = new WebSocket(webSocketDebuggerUrl);
  let nextId = 1;
  const pending = new Map();
  socket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  });
  const opened = new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  return {
    async send(method, params = {}) {
      await opened;
      const id = nextId++;
      socket.send(JSON.stringify({ id, method, params }));
      return await new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
    },
    async evaluate(expression) {
      const result = await this.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) {
        throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text || "evaluation failed");
      }
      return result.result.value;
    },
    close() {
      socket.close();
    }
  };
}

async function startStaticServer(root, port, apiBaseUrl = null) {
  const types = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml" };
  const server = createServer(async (req, res) => {
    const pathname = new URL(req.url, `http://127.0.0.1:${port}`).pathname;
    if (apiBaseUrl && pathname.startsWith("/api/")) {
      const upstream = await fetch(`${apiBaseUrl}${req.url}`, {
        method: req.method,
        headers: req.headers,
        body: req.method === "GET" || req.method === "HEAD" ? undefined : req,
        duplex: req.method === "GET" || req.method === "HEAD" ? undefined : "half"
      });
      res.writeHead(upstream.status, Object.fromEntries(upstream.headers));
      res.end(Buffer.from(await upstream.arrayBuffer()));
      return;
    }
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

async function waitFor(fn, timeoutMs = 8000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      if (await fn()) return;
    } catch {
      // retry until timeout
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error("timeout waiting for local api");
}
