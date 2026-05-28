import { readFile } from "node:fs/promises";
import { join } from "node:path";

const root = process.argv[2] ?? "data/fixtures/public";
const required = {
  "latest-manifest.json": ["schema_version", "generated_at", "export_version", "indexes"]
};

const json = async (path) => JSON.parse(await readFile(join(root, path.replace(/^\//, "")), "utf8"));

for (const [path, keys] of Object.entries(required)) {
  const data = await json(path);
  for (const key of keys) {
    if (!(key in data)) throw new Error(`${path} missing ${key}`);
  }
}

const manifest = await json("latest-manifest.json");
if (manifest.schema_version !== "public-manifest/v1") throw new Error("invalid manifest schema");
for (const key of ["videos_latest", "tags"]) {
  if (!manifest.indexes?.[key]) throw new Error(`manifest missing indexes.${key}`);
}

const videos = await json(manifest.indexes.videos_latest);
if (videos.schema_version !== "public-video-list/v1") throw new Error("invalid videos schema");
for (const item of videos.items) {
  for (const key of ["video_id", "title", "published_at", "tags", "detail_path", "wordcloud_available", "timestamp_available"]) {
    if (!(key in item)) throw new Error(`video item ${item.video_id ?? "(unknown)"} missing ${key}`);
  }
  if (item.detail_path.includes("fixture") && !item.detail_path.startsWith("/data/")) {
    throw new Error(`detail_path must be public data path: ${item.detail_path}`);
  }
  const detail = await json(item.detail_path);
  if (detail.schema_version !== "public-video-detail/v1") throw new Error(`invalid detail schema for ${item.video_id}`);
  if (!detail.video?.youtube_url) throw new Error(`detail ${item.video_id} missing youtube_url`);
  if (!("wordcloud_url" in (detail.chat_summary || {}))) throw new Error(`detail ${item.video_id} missing chat_summary.wordcloud_url`);
  for (const timestamp of detail.timestamps || []) {
    for (const key of ["offset_sec", "label", "source"]) {
      if (!(key in timestamp)) throw new Error(`timestamp for ${item.video_id} missing ${key}`);
    }
  }
}

const tags = await json(manifest.indexes.tags);
if (tags.schema_version !== "public-tag-list/v1") throw new Error("invalid tags schema");
for (const item of tags.items) {
  for (const key of ["tag_id", "label", "video_count", "category"]) {
    if (!(key in item)) throw new Error(`tag item missing ${key}`);
  }
}

console.log(`public contract is valid: ${root}`);
