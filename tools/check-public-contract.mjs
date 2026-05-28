import { readFile } from "node:fs/promises";

const required = {
  "data/fixtures/public/latest-manifest.json": ["schema_version", "generated_at", "export_version", "indexes"],
  "data/fixtures/public/data/v/dev-fixture/public/index/videos-latest.json": ["schema_version", "generated_at", "items"],
  "data/fixtures/public/data/v/dev-fixture/public/index/tags.json": ["schema_version", "generated_at", "items"]
};

const json = async (path) => JSON.parse(await readFile(path, "utf8"));

for (const [path, keys] of Object.entries(required)) {
  const data = await json(path);
  for (const key of keys) {
    if (!(key in data)) throw new Error(`${path} missing ${key}`);
  }
}

const manifest = await json("data/fixtures/public/latest-manifest.json");
if (manifest.schema_version !== "public-manifest/v1") throw new Error("invalid manifest schema");

const videos = await json("data/fixtures/public/data/v/dev-fixture/public/index/videos-latest.json");
if (videos.schema_version !== "public-video-list/v1") throw new Error("invalid videos schema");
for (const item of videos.items) {
  for (const key of ["video_id", "title", "published_at", "tags", "detail_path"]) {
    if (!(key in item)) throw new Error(`video item ${item.video_id ?? "(unknown)"} missing ${key}`);
  }
  if (item.detail_path.includes("fixture") && !item.detail_path.startsWith("/data/")) {
    throw new Error(`detail_path must be public data path: ${item.detail_path}`);
  }
}

const tags = await json("data/fixtures/public/data/v/dev-fixture/public/index/tags.json");
if (tags.schema_version !== "public-tag-list/v1") throw new Error("invalid tags schema");
for (const item of tags.items) {
  for (const key of ["tag_id", "label", "video_count", "category"]) {
    if (!(key in item)) throw new Error(`tag item missing ${key}`);
  }
}

console.log("public contract fixtures are valid");
