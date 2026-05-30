import { access, readFile } from "node:fs/promises";
import { join } from "node:path";

const root = process.cwd();

const files = {
  readme: "README.md",
  api: "apps/api/src/diopside_api/handler.py",
  worker: "apps/workers/static-exporter/src/static_exporter/pipeline.py",
  staticExporter: "apps/workers/static-exporter/src/static_exporter/handler.py",
  chat: "apps/shared/src/diopside_core/chat.py",
};

const expected = {
  apiRoutes: [
    ["GET", "/api/health"],
    ["GET", "/api/config"],
    ["GET", "/api/home"],
    ["GET", "/api/videos"],
    ["GET", "/api/tags"],
    ["GET", "/api/archive-calendar"],
    ["GET", "/api/random-videos"],
    ["GET", "/api/videos/{video_id}"],
    ["GET", "/api/videos/{video_id}/artifacts"],
    ["POST", "/api/admin/session"],
    ["GET", "/api/admin/me"],
    ["GET", "/api/admin/jobs"],
    ["GET", "/api/admin/jobs/{job_id}"],
    ["GET", "/api/admin/channels"],
    ["GET", "/api/admin/quota-usage"],
    ["PUT", "/api/admin/channels/{channel_id}"],
    ["POST", "/api/admin/artifacts/presigned-url"],
    ["POST", "/api/admin/jobs/metadata-sync"],
    ["POST", "/api/admin/jobs/live-status-scan"],
    ["POST", "/api/admin/jobs/chat-collect"],
    ["POST", "/api/admin/jobs/chat-normalize"],
    ["POST", "/api/admin/jobs/rebuild-artifacts"],
    ["POST", "/api/admin/jobs/static-export"],
    ["POST", "/api/admin/jobs/{job_id}/retry"],
    ["POST", "/api/admin/jobs/{job_id}/cancel"],
  ],
  apiSchemas: [
    "public-config/v1",
    "public-home/v1",
    "public-video-list/v1",
    "public-tag-list/v1",
    "public-archive-calendar/v1",
    "public-random-videos/v1",
    "public-video-detail/v1",
    "public-video-artifacts/v1",
    "admin-session/v1",
    "admin-job-list/v1",
    "admin-job-detail/v1",
    "admin-channel-list/v1",
    "admin-quota-usage/v1",
    "admin-channel-config/v1",
    "admin-artifact-presigned-url/v1",
  ],
  publicDataPaths: [
    "/data/latest-manifest.json",
    "/data/v/{export_version}/public/index/videos-latest.json",
    "/data/v/{export_version}/public/index/tags.json",
    "/data/v/{export_version}/public/search/videos-{year}.json",
    "/data/v/{export_version}/public/videos/{video_id}.json",
    "/data/v/{export_version}/public/artifacts/wordcloud/{video_id}.svg",
  ],
  publicDataSchemas: [
    "public-manifest/v1",
    "public-video-list/v1",
    "public-tag-list/v1",
    "public-video-search/v1",
    "public-video-detail/v1",
  ],
  adminJobApiTypes: [
    "metadata_sync",
    "live_status_scan",
    "chat_collect",
    "chat_normalize",
    "rebuild_artifacts",
    "static_export",
    "retry_job",
    "cancel_job",
  ],
  workerJobTypes: [
    "metadata_sync",
    "live_status_scan",
    "chat_collect",
    "chat_normalize",
    "rebuild_artifacts",
    "static_export",
    "retry_job",
    "cancel_job",
    "quota_rollup",
    "cleanup",
  ],
  chatRequiredKeys: [
    "schema_version",
    "message_id",
    "video_id",
    "source",
    "message_type",
    "author",
    "author_external_channel_id",
    "author_name",
    "author_badges",
    "timestamp_usec",
    "timestamp_text",
    "offset_msec",
    "video_offset_time_msec",
    "message_runs",
    "plain_text",
    "message_text",
    "paid",
    "purchase_amount_text",
    "sticker",
    "raw_ref",
    "raw_renderer_type",
    "raw_renderer",
    "parse_warning",
    "collected_at",
  ],
};

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

const read = async (path) => readFile(join(root, path), "utf8");
const exists = async (path) => access(path).then(() => true, () => false);

const readme = await read(files.readme);
const api = await read(files.api);
const worker = await read(files.worker);
const staticExporter = await read(files.staticExporter);
const chat = await read(files.chat);

for (const [method, route] of expected.apiRoutes) {
  assert(readme.includes(`\`${method} ${route}\``), `README missing API route: ${method} ${route}`);
}

for (const schema of expected.apiSchemas) {
  assert(readme.includes(`\`${schema}\``), `README missing API schema: ${schema}`);
  assert(api.includes(`"${schema}"`) || staticExporter.includes(`"${schema}"`), `implementation missing API/public schema: ${schema}`);
}

for (const path of expected.publicDataPaths) {
  assert(readme.includes(`\`${path}\``), `README missing public data path: ${path}`);
}

for (const schema of expected.publicDataSchemas) {
  assert(readme.includes(`\`${schema}\``), `README missing public data schema: ${schema}`);
  assert(staticExporter.includes(`"${schema}"`), `static exporter missing public data schema: ${schema}`);
}

for (const jobType of expected.adminJobApiTypes) {
  assert(readme.includes(`\`${jobType}\``), `README missing admin job type: ${jobType}`);
  assert(api.includes(`"${jobType}"`), `API handler missing admin job type: ${jobType}`);
  assert(worker.includes(`"${jobType}"`), `worker missing admin job type: ${jobType}`);
}

for (const jobType of expected.workerJobTypes) {
  assert(readme.includes(`\`${jobType}\``), `README missing worker job type: ${jobType}`);
  assert(worker.includes(`"${jobType}"`), `worker missing job type: ${jobType}`);
}

assert(readme.includes("`chat-message/v1`"), "README missing chat-message/v1 schema version");
assert(chat.includes('CHAT_MESSAGE_SCHEMA_VERSION = "chat-message/v1"'), "chat implementation missing chat-message/v1 schema version");

for (const key of expected.chatRequiredKeys) {
  assert(readme.includes(`\`${key}\``), `README missing normalized chat key: ${key}`);
  assert(chat.includes(`"${key}"`), `chat implementation missing normalized chat key: ${key}`);
}

assert(staticExporter.includes("latest-manifest.json"), "static exporter missing latest-manifest.json");
assert(staticExporter.includes("/data/v/"), "static exporter missing versioned /data/v path");
assert(staticExporter.includes("public/index/videos-latest.json"), "static exporter missing videos-latest public path");
assert(staticExporter.includes("public/index/tags.json"), "static exporter missing tags public path");
assert(staticExporter.includes("public/search/videos-"), "static exporter missing search public path");
assert(staticExporter.includes("public/videos/"), "static exporter missing video detail public path");
assert(staticExporter.includes("public/artifacts/wordcloud/"), "static exporter missing wordcloud public path");

const designDoc = process.env.DIOPSIDE_DESIGN_DOC;
if (designDoc) {
  assert(await exists(designDoc), `DIOPSIDE_DESIGN_DOC does not exist: ${designDoc}`);
  const design = await readFile(designDoc, "utf8");
  for (const token of [
    "CloudFront + S3",
    "DynamoDB",
    "S3 JSONL",
    "OpenSearch",
    "RDB",
    "EventBridge Scheduler",
    "SQS",
    "Lambda",
    "chat-message/v1",
    "/api/health",
    "/api/videos",
    "/api/admin/jobs",
    "/data/latest-manifest.json",
    "/data/v/{export_version}",
  ]) {
    assert(design.includes(token), `design doc missing expected design premise: ${token}`);
  }
}

console.log("docs consistency contract is valid");
