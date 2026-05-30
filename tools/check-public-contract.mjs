import { access, readFile } from "node:fs/promises";
import { join } from "node:path";
import { createHash } from "node:crypto";

const root = process.argv[2] ?? "data/fixtures/public";

const json = async (path) => JSON.parse(await readFile(join(root, path.replace(/^\//, "")), "utf8"));
const readText = async (path) => readFile(join(root, path.replace(/^\//, "")), "utf8");
const readBinary = async (path) => readFile(join(root, path.replace(/^\//, "")));
const exists = async (path) => access(join(root, path.replace(/^\//, ""))).then(() => true, () => false);
const sha256 = async (path) => createHash("sha256").update(await readFile(join(root, path.replace(/^\//, "")))).digest("hex");

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const manifest = await json("latest-manifest.json");
requireKeys(manifest, ["schema_version", "generated_at", "export_version", "base_path", "indexes"], "latest-manifest.json");
assert(manifest.schema_version === "public-manifest/v1", "invalid manifest schema");
assert(typeof manifest.export_version === "string" && manifest.export_version.length > 0, "manifest export_version must be non-empty string");
assert(manifest.base_path === `/data/v/${manifest.export_version}`, `manifest base_path must match export_version: ${manifest.base_path}`);
validateStaticPathManifest(manifest);

const publicBasePath = `${manifest.base_path}/public`;
for (const key of ["videos_latest", "tags"]) {
  assert(manifest.indexes?.[key], `manifest missing indexes.${key}`);
  assertVersionedPath(manifest.indexes[key], `${publicBasePath}/`, `manifest indexes.${key}`);
}

const searchIndexes = Object.entries(manifest.indexes).filter(([key]) => key.startsWith("search_"));
assert(searchIndexes.length > 0, "manifest must include at least one search index");
for (const [key, path] of searchIndexes) {
  assert(/^search_\d{4}$|^search_unknown$/.test(key), `invalid search index key: ${key}`);
  assertVersionedPath(path, `${publicBasePath}/search/videos-`, `manifest indexes.${key}`);
}

const videos = await json(manifest.indexes.videos_latest);
requireKeys(videos, ["schema_version", "generated_at", "items"], manifest.indexes.videos_latest);
assert(videos.schema_version === "public-video-list/v1", "invalid videos schema");
assert(Array.isArray(videos.items), "videos items must be array");
const videoIds = new Set();
for (const item of videos.items) {
  for (const key of ["video_id", "title", "published_at", "tags", "detail_path", "wordcloud_available", "timestamp_available"]) {
    assert(key in item, `video item ${item.video_id ?? "(unknown)"} missing ${key}`);
  }
  assert(typeof item.video_id === "string" && item.video_id.length > 0, "video item video_id must be non-empty string");
  assert(!videoIds.has(item.video_id), `duplicate video_id in video list: ${item.video_id}`);
  videoIds.add(item.video_id);
  assert(typeof item.title === "string", `video item ${item.video_id} title must be string`);
  assert(Array.isArray(item.tags), `video item ${item.video_id} tags must be array`);
  assert(typeof item.wordcloud_available === "boolean", `video item ${item.video_id} wordcloud_available must be boolean`);
  assert(typeof item.timestamp_available === "boolean", `video item ${item.video_id} timestamp_available must be boolean`);
  assertVersionedPath(item.detail_path, `${publicBasePath}/videos/`, `video item ${item.video_id} detail_path`);

  const detail = await json(item.detail_path);
  await validateVideoDetail(detail, item, publicBasePath);
}

const tags = await json(manifest.indexes.tags);
requireKeys(tags, ["schema_version", "generated_at", "items"], manifest.indexes.tags);
assert(tags.schema_version === "public-tag-list/v1", "invalid tags schema");
assert(Array.isArray(tags.items), "tags items must be array");
for (const item of tags.items) {
  for (const key of ["tag_id", "label", "video_count", "category"]) {
    assert(key in item, `tag item missing ${key}`);
  }
  assert(typeof item.tag_id === "string" && item.tag_id.length > 0, "tag item tag_id must be non-empty string");
  assert(typeof item.label === "string" && item.label.length > 0, `tag item ${item.tag_id} label must be non-empty string`);
  assert(Number.isInteger(item.video_count) && item.video_count >= 0, `tag item ${item.tag_id} video_count must be non-negative integer`);
  assert(typeof item.category === "string" && item.category.length > 0, `tag item ${item.tag_id} category must be non-empty string`);
}

for (const [, path] of searchIndexes) {
  const search = await json(path);
  requireKeys(search, ["schema_version", "generated_at", "items"], path);
  assert(search.schema_version === "public-video-search/v1", `invalid search schema: ${path}`);
  assert(Array.isArray(search.items), `search items must be array: ${path}`);
  for (const item of search.items) {
    requireKeys(item, ["video_id", "title", "tags", "published_at"], `${path} item`);
    assert(videoIds.has(item.video_id), `search item references unknown video_id: ${item.video_id}`);
    assert(Array.isArray(item.tags), `search item ${item.video_id} tags must be array`);
  }
}

await validateStaticAliases(manifest, videos, tags, videoIds, publicBasePath);

console.log(`public contract is valid: ${root}`);

async function validateStaticAliases(manifest, versionedVideos, versionedTags, videoIds, publicBasePath) {
  const staticPaths = manifest.static_paths;
  const homeEntry = staticPaths["STATIC-001"];
  await validateStaticEntry(homeEntry, "STATIC-001", { versionedRequired: true });
  const home = await json(homeEntry.path);
  requireKeys(home, ["schema_version", "generated_at", "latest_videos", "popular_tags"], "STATIC-001 home");
  assert(home.schema_version === "public-home/v1", "invalid STATIC-001 home schema");
  assert(Array.isArray(home.latest_videos), "STATIC-001 latest_videos must be array");
  assert(Array.isArray(home.popular_tags), "STATIC-001 popular_tags must be array");

  const videosEntry = staticPaths["STATIC-002"];
  await validateStaticEntry(videosEntry, "STATIC-002", { versionedRequired: true });
  const aliasVideos = await json(videosEntry.path);
  requireKeys(aliasVideos, ["schema_version", "generated_at", "items"], "STATIC-002 videos");
  assert(aliasVideos.schema_version === "public-video-list/v1", "invalid STATIC-002 videos schema");
  assert(aliasVideos.items.length === versionedVideos.items.length, "STATIC-002 item count must match versioned videos_latest");
  for (const item of aliasVideos.items) {
    requireKeys(item, ["video_id", "title", "published_at", "tags", "detail_path", "wordcloud_available", "timestamp_available", "timestamp_path"], `STATIC-002 item ${item.video_id}`);
    assert(videoIds.has(item.video_id), `STATIC-002 references unknown video_id: ${item.video_id}`);
    assert(item.detail_path === `/data/videos/${item.video_id}.json`, `STATIC-002 detail_path must be alias path for ${item.video_id}`);
    assert(item.timestamp_path === `/data/artifacts/timestamps/${item.video_id}.json`, `STATIC-002 timestamp_path must be alias path for ${item.video_id}`);
  }

  const detailEntries = staticPaths["STATIC-003"].items;
  for (const videoId of videoIds) {
    const entry = detailEntries[videoId];
    await validateStaticEntry(entry, `STATIC-003 ${videoId}`, { versionedRequired: true });
    assert(entry.path === `/data/videos/${videoId}.json`, `STATIC-003 path mismatch for ${videoId}`);
    assertVersionedPath(entry.versioned_path, `${publicBasePath}/videos/`, `STATIC-003 ${videoId} versioned_path`);
    const aliasDetail = await json(entry.path);
    await validateVideoDetail(aliasDetail, { video_id: videoId, title: aliasDetail.video.title, wordcloud_available: Boolean(aliasDetail.chat_summary.wordcloud_url), timestamp_available: aliasDetail.timestamps.length > 0 }, publicBasePath);
  }

  const tagsEntry = staticPaths["STATIC-004"];
  await validateStaticEntry(tagsEntry, "STATIC-004", { versionedRequired: true });
  const aliasTags = await json(tagsEntry.path);
  assert(aliasTags.schema_version === "public-tag-list/v1", "invalid STATIC-004 tags schema");
  assert(aliasTags.items.length === versionedTags.items.length, "STATIC-004 item count must match versioned tags");

  const calendarEntries = staticPaths["STATIC-005"].items;
  assert(Object.keys(calendarEntries).length > 0, "STATIC-005 must include at least one calendar year");
  for (const [year, entry] of Object.entries(calendarEntries)) {
    await validateStaticEntry(entry, `STATIC-005 ${year}`, { versionedRequired: true });
    const calendar = await json(entry.path);
    requireKeys(calendar, ["schema_version", "generated_at", "year", "months"], `STATIC-005 ${year}`);
    assert(calendar.schema_version === "public-archive-calendar/v1", `invalid STATIC-005 calendar schema for ${year}`);
    assert(calendar.year === year, `STATIC-005 year mismatch for ${year}`);
    assert(Array.isArray(calendar.months), `STATIC-005 months must be array for ${year}`);
    for (const month of calendar.months) {
      requireKeys(month, ["month", "video_count", "items"], `STATIC-005 ${year} month`);
      assert(month.video_count === month.items.length, `STATIC-005 video_count mismatch for ${year}-${month.month}`);
    }
  }

  const manifestEntry = staticPaths["STATIC-006"];
  assert(manifestEntry.path === "/data/latest-manifest.json", "STATIC-006 path must be latest-manifest.json");
  assert(typeof manifestEntry.checksum_sha256 === "string" && /^[a-f0-9]{64}$/.test(manifestEntry.checksum_sha256), "STATIC-006 checksum must be sha256 hex");
  assert(manifestEntry.checksum_sha256 === manifestPayloadChecksum(manifest), "STATIC-006 canonical manifest checksum mismatch");

  const wordcloudEntries = staticPaths["STATIC-007"].items;
  for (const [videoId, entry] of Object.entries(wordcloudEntries)) {
    await validateStaticEntry(entry, `STATIC-007 ${videoId}`, { versionedRequired: true });
    const wordcloud = await json(entry.path);
    requireKeys(wordcloud, ["schema_version", "video_id", "generated_at", "top_terms", "message_count", "source_png_path"], `STATIC-007 ${videoId}`);
    assert(wordcloud.schema_version === "public-wordcloud/v1", `invalid STATIC-007 wordcloud schema for ${videoId}`);
    assert(wordcloud.video_id === videoId, `STATIC-007 video_id mismatch for ${videoId}`);
    assert(Array.isArray(wordcloud.top_terms), `STATIC-007 top_terms must be array for ${videoId}`);
  }
  requireKeys(staticPaths["STATIC-007"], ["image_items"], "STATIC-007");
  const wordcloudImageEntries = staticPaths["STATIC-007"].image_items;
  for (const [videoId, entry] of Object.entries(wordcloudImageEntries)) {
    await validateStaticEntry(entry, `STATIC-007 image ${videoId}`, { versionedRequired: true });
    assert(entry.path === `/data/artifacts/wordcloud/${videoId}.png`, `STATIC-007 image path mismatch for ${videoId}`);
    assert(entry.versioned_path.endsWith(`/artifacts/wordcloud/${videoId}.png`), `STATIC-007 image versioned path mismatch for ${videoId}`);
    await validatePng(entry.path, `STATIC-007 image ${videoId}`);
  }

  const timestampEntries = staticPaths["STATIC-008"].items;
  for (const videoId of videoIds) {
    const entry = timestampEntries[videoId];
    await validateStaticEntry(entry, `STATIC-008 ${videoId}`, { versionedRequired: true });
    const timestamps = await json(entry.path);
    requireKeys(timestamps, ["schema_version", "video_id", "generated_at", "items"], `STATIC-008 ${videoId}`);
    assert(timestamps.schema_version === "public-timestamp-list/v1", `invalid STATIC-008 timestamp schema for ${videoId}`);
    assert(timestamps.video_id === videoId, `STATIC-008 video_id mismatch for ${videoId}`);
    assert(Array.isArray(timestamps.items), `STATIC-008 items must be array for ${videoId}`);
    for (const item of timestamps.items) validateTimestamp(item, videoId);
  }
}

async function validateVideoDetail(detail, item, publicBasePath) {
  requireKeys(detail, ["schema_version", "video", "chat_summary", "artifacts", "timestamps"], item.detail_path);
  assert(detail.schema_version === "public-video-detail/v1", `invalid detail schema for ${item.video_id}`);
  requireKeys(detail.video, ["video_id", "youtube_url", "title", "published_at", "tags"], `detail ${item.video_id}.video`);
  assert(detail.video.video_id === item.video_id, `detail video_id mismatch for ${item.video_id}`);
  assert(detail.video.title === item.title, `detail title mismatch for ${item.video_id}`);
  assert(Array.isArray(detail.video.tags), `detail ${item.video_id} video.tags must be array`);
  assert(typeof detail.video.youtube_url === "string" && detail.video.youtube_url.startsWith("https://www.youtube.com/watch?v="), `detail ${item.video_id} invalid youtube_url`);

  requireKeys(detail.chat_summary, ["message_count", "wordcloud_url", "top_terms"], `detail ${item.video_id}.chat_summary`);
  assert(Number.isInteger(detail.chat_summary.message_count) && detail.chat_summary.message_count >= 0, `detail ${item.video_id} chat_summary.message_count must be non-negative integer`);
  assert(Array.isArray(detail.chat_summary.top_terms), `detail ${item.video_id} chat_summary.top_terms must be array`);
  assert("wordcloud" in detail.artifacts, `detail ${item.video_id} artifacts missing wordcloud`);
  assert(item.wordcloud_available === Boolean(detail.chat_summary.wordcloud_url), `wordcloud availability mismatch for ${item.video_id}`);

  if (item.wordcloud_available) {
    await validateWordcloud(detail, item, publicBasePath);
  } else {
    assert(detail.chat_summary.wordcloud_url === null, `detail ${item.video_id} wordcloud_url must be null when unavailable`);
    assert(detail.artifacts.wordcloud === null, `detail ${item.video_id} artifacts.wordcloud must be null when unavailable`);
  }

  assert(Array.isArray(detail.timestamps), `detail ${item.video_id} timestamps must be array`);
  assert(item.timestamp_available === (detail.timestamps.length > 0), `timestamp availability mismatch for ${item.video_id}`);
  for (const timestamp of detail.timestamps) {
    validateTimestamp(timestamp, item.video_id);
  }
}

async function validateWordcloud(detail, item, publicBasePath) {
  const artifact = detail.artifacts.wordcloud;
  requireKeys(artifact, ["path", "versioned_path", "content_type"], `detail ${item.video_id}.artifacts.wordcloud`);
  assert(artifact.path === detail.chat_summary.wordcloud_url, `wordcloud artifact path mismatch for ${item.video_id}`);
  assert(artifact.content_type === "image/png", `wordcloud content_type mismatch for ${item.video_id}`);
  assert(artifact.path === `/data/artifacts/wordcloud/${item.video_id}.png`, `wordcloud path must be STATIC-007 PNG alias for ${item.video_id}`);
  assertVersionedPath(artifact.versioned_path, `${publicBasePath}/artifacts/wordcloud/`, `detail ${item.video_id} wordcloud versioned path`);
  assert(artifact.versioned_path.endsWith(`/${item.video_id}.png`), `wordcloud versioned path must end with video_id.png for ${item.video_id}`);
  await validatePng(artifact.path, `detail ${item.video_id} wordcloud`);

  const svgArtifact = detail.artifacts.wordcloud_svg;
  requireKeys(svgArtifact, ["path", "content_type"], `detail ${item.video_id}.artifacts.wordcloud_svg`);
  assert(svgArtifact.content_type === "image/svg+xml", `wordcloud_svg content_type mismatch for ${item.video_id}`);
  assertVersionedPath(svgArtifact.path, `${publicBasePath}/artifacts/wordcloud/`, `detail ${item.video_id} wordcloud_svg path`);
  assert(svgArtifact.path.endsWith(`/${item.video_id}.svg`), `wordcloud_svg path must end with video_id.svg for ${item.video_id}`);
  assert(await exists(svgArtifact.path), `wordcloud SVG missing for ${item.video_id}: ${svgArtifact.path}`);
  const svg = await readText(svgArtifact.path);
  assert(svg.trimStart().startsWith("<svg "), `wordcloud SVG must start with <svg for ${item.video_id}`);
  assert(svg.includes("diopside wordcloud"), `wordcloud SVG missing accessible title for ${item.video_id}`);
}

async function validatePng(path, label) {
  assert(await exists(path), `${label} PNG missing: ${path}`);
  const data = await readBinary(path);
  assert(data.length > 64, `${label} PNG must not be empty`);
  assert(data[0] === 0x89 && data[1] === 0x50 && data[2] === 0x4e && data[3] === 0x47, `${label} PNG signature mismatch`);
}

function validateStaticPathManifest(manifest) {
  requireKeys(manifest, ["static_paths"], "latest-manifest.json");
  for (const id of ["STATIC-001", "STATIC-002", "STATIC-003", "STATIC-004", "STATIC-005", "STATIC-006", "STATIC-007", "STATIC-008"]) {
    assert(id in manifest.static_paths, `manifest missing static_paths.${id}`);
  }
}

async function validateStaticEntry(entry, label, { versionedRequired }) {
  requireKeys(entry, ["path", "versioned_path", "checksum_sha256"], label);
  assert(typeof entry.path === "string" && entry.path.startsWith("/data/"), `${label} path must be /data path`);
  assert(await exists(entry.path), `${label} path missing: ${entry.path}`);
  if (versionedRequired) {
    assertVersionedPath(entry.versioned_path, "/data/v/", `${label} versioned_path`);
    assert(await exists(entry.versioned_path), `${label} versioned_path missing: ${entry.versioned_path}`);
  }
  assert(entry.checksum_sha256 === await sha256(entry.path), `${label} checksum mismatch for ${entry.path}`);
}

function manifestPayloadChecksum(manifest) {
  const payload = JSON.parse(JSON.stringify(manifest));
  payload.static_paths["STATIC-006"].checksum_sha256 = null;
  return createHash("sha256").update(JSON.stringify(sortKeys(payload))).digest("hex");
}

function sortKeys(value) {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).sort(([left], [right]) => left.localeCompare(right)).map(([key, item]) => [key, sortKeys(item)]));
  }
  return value;
}

function validateTimestamp(timestamp, videoId) {
  requireKeys(timestamp, ["offset_sec", "label", "source", "score", "evidence_terms", "message_count"], `timestamp for ${videoId}`);
  assert(Number.isInteger(timestamp.offset_sec) && timestamp.offset_sec >= 0, `timestamp for ${videoId} offset_sec must be non-negative integer`);
  assert(typeof timestamp.label === "string" && timestamp.label.length > 0, `timestamp for ${videoId} label must be non-empty string`);
  assert(typeof timestamp.source === "string" && timestamp.source.length > 0, `timestamp for ${videoId} source must be non-empty string`);
  assert(typeof timestamp.score === "number" && Number.isFinite(timestamp.score), `timestamp for ${videoId} score must be finite number`);
  assert(Array.isArray(timestamp.evidence_terms), `timestamp for ${videoId} evidence_terms must be array`);
  assert(Number.isInteger(timestamp.message_count) && timestamp.message_count >= 0, `timestamp for ${videoId} message_count must be non-negative integer`);
}

function requireKeys(value, keys, label) {
  assert(value && typeof value === "object" && !Array.isArray(value), `${label} must be object`);
  for (const key of keys) {
    assert(key in value, `${label} missing ${key}`);
  }
}

function assertVersionedPath(path, prefix, label) {
  assert(typeof path === "string" && path.startsWith(prefix), `${label} must start with ${prefix}: ${path}`);
  assert(!path.includes(".."), `${label} must not contain path traversal: ${path}`);
}
