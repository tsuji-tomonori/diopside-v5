import { mkdir, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";

const baseUrl = requiredEnv("DIOPSIDE_E2E_BASE_URL").replace(/\/$/, "");
const adminToken = process.env.DIOPSIDE_ADMIN_TOKEN;
const csrfToken = process.env.DIOPSIDE_ADMIN_CSRF_TOKEN;
const out = process.env.DIOPSIDE_E2E_PUBLIC_DATA_DIR || "build/post-deploy-public-data";

await smokePublic(baseUrl, out);
if (adminToken && csrfToken) {
  await smokeAdmin(baseUrl, adminToken, csrfToken, out);
} else {
  console.log("admin smoke skipped: DIOPSIDE_ADMIN_TOKEN and DIOPSIDE_ADMIN_CSRF_TOKEN are not both set");
}
console.log(`post-deploy smoke passed for ${baseUrl}`);

async function smokePublic(url, outDir) {
  await rm(outDir, { recursive: true, force: true });
  await mkdir(outDir, { recursive: true });
  const html = await text(`${url}/`);
  if (!html.includes("diopside")) throw new Error("home html does not include diopside");
  const health = await json(`${url}/api/health`);
  if (health.service !== "diopside" || health.status !== "ok") throw new Error("health failed");
  const home = await json(`${url}/api/home`);
  if (!Array.isArray(home.latest_videos) || !Array.isArray(home.popular_tags)) throw new Error("api home response is invalid");
  const apiVideos = await json(`${url}/api/videos?limit=1`);
  if (!apiVideos.items?.length) throw new Error("api videos empty");
  const apiDetail = await json(`${url}/api/videos/${apiVideos.items[0].video_id}`);
  if (!apiDetail.video?.youtube_url) throw new Error("api video detail missing youtube_url");
  const manifest = await json(`${url}/data/latest-manifest.json`);
  await writeJson(join(outDir, "latest-manifest.json"), manifest);
  const videos = await json(`${url}${manifest.indexes.videos_latest}`);
  const tags = await json(`${url}${manifest.indexes.tags}`);
  await writeJson(join(outDir, manifest.indexes.videos_latest.replace(/^\//, "")), videos);
  await writeJson(join(outDir, manifest.indexes.tags.replace(/^\//, "")), tags);
  if (!videos.items?.length) throw new Error("videos index is empty");
  for (const item of videos.items) {
    const detail = await json(`${url}${item.detail_path}`);
    await writeJson(join(outDir, item.detail_path.replace(/^\//, "")), detail);
    if (detail.chat_summary?.wordcloud_url) {
      await text(`${url}${detail.chat_summary.wordcloud_url}`);
    }
  }
  const contract = spawnSync("node", ["tools/check-public-contract.mjs", outDir], { stdio: "inherit" });
  if (contract.status !== 0) throw new Error("public data contract check failed");
}

async function smokeAdmin(url, token, csrf, outDir) {
  const beforeManifest = await json(`${url}/data/latest-manifest.json`);
  const idempotency = `post-deploy-static-export-${Date.now()}`;
  const created = await json(`${url}/api/admin/jobs/static-export`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      Authorization: `Bearer ${token}`,
      "X-CSRF-Token": csrf
    },
    body: JSON.stringify({ idempotency_key: idempotency, scope: "all" })
  });
  if (created.job_type !== "static_export" || created.derived_state !== "queued") throw new Error("static-export job did not queue");
  const completed = await waitForJob(url, token, created.job_id);
  if (completed.item.derived_state !== "succeeded") throw new Error(`static-export job did not complete: ${completed.item.derived_state}`);
  const jobs = await json(`${url}/api/admin/jobs`, { headers: { Authorization: `Bearer ${token}` } });
  if (!jobs.items?.some((item) => item.job_id === created.job_id)) throw new Error("admin job list missing created job");
  const detail = await json(`${url}/api/admin/jobs/${created.job_id}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!detail.item?.events?.length) throw new Error("admin job detail missing events");
  const quota = await json(`${url}/api/admin/quota-usage`, { headers: { Authorization: `Bearer ${token}` } });
  if (!Array.isArray(quota.items)) throw new Error("quota usage response must include items array");
  const afterManifest = await waitForManifestRefresh(url, beforeManifest);
  await writeJson(join(outDir, "latest-manifest-after-static-export.json"), afterManifest);
  if (afterManifest.generated_at === beforeManifest.generated_at && afterManifest.export_version === beforeManifest.export_version) {
    throw new Error("latest-manifest.json was not refreshed after static-export job completion");
  }
  const latest = await json(`${url}${afterManifest.indexes.videos_latest}`);
  if (!latest.items?.length) throw new Error("versioned public JSON after static-export is empty");
}

async function waitForJob(url, token, jobId) {
  const deadline = Date.now() + Number(process.env.DIOPSIDE_POST_DEPLOY_JOB_TIMEOUT_MS || 180000);
  let detail;
  while (Date.now() < deadline) {
    detail = await json(`${url}/api/admin/jobs/${jobId}`, { headers: { Authorization: `Bearer ${token}` } });
    const state = detail.item?.derived_state;
    if (state === "succeeded") return detail;
    if (["failed", "cancelled"].includes(state)) throw new Error(`job ${jobId} ended as ${state}`);
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
  throw new Error(`job ${jobId} did not complete before timeout; last detail: ${JSON.stringify(detail)}`);
}

async function waitForManifestRefresh(url, beforeManifest) {
  const deadline = Date.now() + Number(process.env.DIOPSIDE_POST_DEPLOY_MANIFEST_TIMEOUT_MS || 180000);
  let manifest;
  while (Date.now() < deadline) {
    manifest = await json(`${url}/data/latest-manifest.json`);
    if (manifest.generated_at !== beforeManifest.generated_at || manifest.export_version !== beforeManifest.export_version) {
      return manifest;
    }
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
  throw new Error(`latest-manifest.json was not refreshed before timeout; last manifest: ${JSON.stringify(manifest)}`);
}

async function json(url, options = {}) {
  const res = await fetch(url, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`${url} returned ${res.status}: ${JSON.stringify(body)}`);
  return body;
}

async function text(url) {
  const res = await fetch(url);
  const body = await res.text();
  if (!res.ok) throw new Error(`${url} returned ${res.status}: ${body.slice(0, 160)}`);
  return body;
}

async function writeJson(path, value) {
  const dir = dirname(path);
  if (dir !== ".") await mkdir(dir, { recursive: true });
  await writeFile(path, JSON.stringify(value, null, 2) + "\n", "utf8");
}

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}
