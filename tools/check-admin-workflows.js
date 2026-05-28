import { createLocalApi } from "../apps/api/src/local-api.js";
import { assert } from "./lib.js";

const api = createLocalApi();
const adminCsrf = csrf("admin-1");
const ownerCsrf = csrf("user-owner");

const importResponse = api.request("admin-1", "startUserImport", {
  csrf_token: adminCsrf,
  rows: [
    { action: "create", user_id: "user-import-created", email: "created@example.test", display_name: "Created User" },
    { action: "update", email: "owner@example.test", display_name: "Updated Owner", department: "acceptance" },
    { action: "delete", email: "outsider@example.test" },
    { action: "create", display_name: "Missing Email" }
  ]
});
assert(importResponse.status === 202, "user import must be accepted");
const importJob = importResponse.body.import;
assert(importJob.result_s3_prefix.startsWith("s3://saphnexa-local/user-import/"), "user import result prefix missing");
assert(importJob.result_report_json.created === 1, "user import created count mismatch");
assert(importJob.result_report_json.updated === 1, "user import updated count mismatch");
assert(importJob.result_report_json.deleted === 1, "user import deleted count mismatch");
assert(importJob.result_report_json.failed === 1, "user import failed count mismatch");
assert(importJob.result_report_json.error_rows_s3_uri.endsWith("error-rows.jsonl"), "user import error row report missing");
const importRows = api.request("admin-1", "getUserImport", { import_id: importJob.import_id }).body.rows;
assert(importRows.length === 4, "user import row count mismatch");
assert(importRows.filter((row) => row.status === "failed").length === 1, "user import failed row coverage mismatch");

const documentInputs = [
  documentInput("doc-local-1", "ver-1", "local-1.pdf"),
  documentInput("doc-local-2", "ver-1", "local-2.pdf"),
  documentInput("doc-local-3", "ver-1", "local-3.pdf"),
  documentInput("doc-versioned", "ver-1", "versioned-v1.pdf"),
  documentInput("doc-versioned", "ver-2", "versioned-v2.pdf")
];
for (const input of documentInputs.slice(0, 4)) {
  const created = api.request("admin-1", "createDocument", { csrf_token: adminCsrf, ...input });
  assert(created.status === 202, `document registration failed: ${input.document_id}/${input.version_id}`);
}
const v2 = api.request("admin-1", "createDocumentVersion", { csrf_token: adminCsrf, document_id: "doc-versioned", ...documentInputs[4] });
assert(v2.status === 202, "document version v2 must be accepted");
assert(api.store.state.ingestion_jobs.length === 5, "document registration must create 5 ingestion jobs");
for (const job of api.store.state.ingestion_jobs) {
  assert(job.raw_s3_uri.startsWith("s3://saphnexa-local/raw/"), `raw URI missing: ${job.job_id}`);
  assert(job.parsed_s3_prefix.startsWith("s3://saphnexa-local/parsed/"), `parsed prefix missing: ${job.job_id}`);
  const version = api.store.state.document_versions.find((item) => item.document_id === job.document_id && item.version_id === job.version_id);
  assert(version?.metadata_json?.document_id === job.document_id, `metadata document_id mismatch: ${job.job_id}`);
}

const activated = api.request("admin-1", "activateDocumentVersion", { csrf_token: adminCsrf, document_id: "doc-versioned", version_id: "ver-2" });
assert(activated.status === 200, "document version activation must succeed");
assert(api.store.state.document_versions.find((item) => item.document_id === "doc-versioned" && item.version_id === "ver-2").status === "active", "new version must be active");
assert(api.store.state.document_versions.find((item) => item.document_id === "doc-versioned" && item.version_id === "ver-1").status === "archived", "old version must be archived");

for (let index = 0; index < 3; index += 1) {
  const evaluation = api.request("admin-1", "startEvaluationRun", { csrf_token: adminCsrf, dataset_id: "dataset-local-golden" });
  assert(evaluation.status === 202, "evaluation run must be accepted");
  const metrics = evaluation.body.evaluation_run.metrics_json;
  assert(metrics.retrieval && metrics.generation && metrics.end_to_end, "evaluation metrics must include three categories");
  assert(evaluation.body.evaluation_run.artifact_s3_prefix.startsWith("s3://saphnexa-local/evaluation/"), "evaluation artifact prefix missing");
}
assert(api.store.state.evaluation_runs.length === 3, "evaluation run count mismatch");

const chatId = api.request("user-owner", "createChatSession", { csrf_token: ownerCsrf, title: "audit chat" }).body.chat.chat_id;
assert(api.request("user-owner", "addChatParticipant", { csrf_token: ownerCsrf, chat_id: chatId, user_id: "user-viewer" }).status === 201, "chat share must succeed");
const question = api.request("user-owner", "submitQuestion", {
  csrf_token: ownerCsrf,
  chat_id: chatId,
  question: "Saphnexa は何をするシステムか",
  retrieval_policy: { top_k: 10, allowed_acl_scope_ids: ["user:user-owner"] }
});
assert(question.status === 202, "question submission must be accepted");
assert(api.request("admin-1", "listPublishedArtifacts").status === 200, "admin artifact list must succeed");
assert(api.request("admin-1", "issueArtifactAccessCookie", { csrf_token: adminCsrf }).status === 201, "artifact cookie must be issued");

for (const eventName of ["admin.user_import.updated", "admin.ingestion.updated", "admin.evaluation.updated", "admin.artifact.published"]) {
  assert(api.store.state.admin_events.some((event) => event.event_name === eventName), `admin event missing: ${eventName}`);
}
for (const category of ["admin_operation", "document_publish", "artifact_access", "chat_share", "tools_execution", "evaluation"]) {
  assert(api.store.state.audit_events.some((event) => event.category === category), `audit category missing: ${category}`);
}

console.log("admin workflow check passed");

function csrf(userId) {
  return api.request(userId, "getMe").body.csrf_token;
}

function documentInput(document_id, version_id, file_name) {
  return {
    title: document_id,
    document_id,
    version_id,
    file_name,
    metadata: { document_id, version: version_id, acl_scope: "admin", status: "uploaded" },
    acl_scope_id: "admin"
  };
}
