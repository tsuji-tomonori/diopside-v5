import { access, readFile } from "node:fs/promises";
import { join } from "node:path";

const root = process.argv[2] ?? "data/fixtures/public";

const json = async (path) => JSON.parse(await readFile(join(root, path.replace(/^\//, "")), "utf8"));
const readText = async (path) => readFile(join(root, path.replace(/^\//, "")), "utf8");
const exists = async (path) => access(join(root, path.replace(/^\//, ""))).then(() => true, () => false);

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const manifest = await json("latest-manifest.json");
requireKeys(manifest, ["schema_version", "generated_at", "export_version", "base_path", "indexes"], "latest-manifest.json");
assert(manifest.schema_version === "public-manifest/v1", "invalid manifest schema");
assert(typeof manifest.export_version === "string" && manifest.export_version.length > 0, "manifest export_version must be non-empty string");
assert(manifest.base_path === `/data/v/${manifest.export_version}`, `manifest base_path must match export_version: ${manifest.base_path}`);

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

console.log(`public contract is valid: ${root}`);

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
  requireKeys(artifact, ["path", "content_type"], `detail ${item.video_id}.artifacts.wordcloud`);
  assert(artifact.path === detail.chat_summary.wordcloud_url, `wordcloud artifact path mismatch for ${item.video_id}`);
  assert(artifact.content_type === "image/svg+xml", `wordcloud content_type mismatch for ${item.video_id}`);
  assertVersionedPath(artifact.path, `${publicBasePath}/artifacts/wordcloud/`, `detail ${item.video_id} wordcloud path`);
  assert(artifact.path.endsWith(`/${item.video_id}.svg`), `wordcloud path must end with video_id.svg for ${item.video_id}`);
  assert(await exists(artifact.path), `wordcloud SVG missing for ${item.video_id}: ${artifact.path}`);
  const svg = await readText(artifact.path);
  assert(svg.trimStart().startsWith("<svg "), `wordcloud SVG must start with <svg for ${item.video_id}`);
  assert(svg.includes("diopside wordcloud"), `wordcloud SVG missing accessible title for ${item.video_id}`);
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
