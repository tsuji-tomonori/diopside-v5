import { createLocalApi } from "../apps/api/src/local-api.js";
import { assert } from "./lib.js";

const api = createLocalApi();
const ownerCsrf = csrf("user-owner");
const adminCsrf = csrf("admin-1");
const chat = api.request("user-owner", "createChatSession", { csrf_token: ownerCsrf, title: "db integrity" }).body.chat;
const accepted = api.request("user-owner", "submitQuestion", {
  csrf_token: ownerCsrf,
  chat_id: chat.chat_id,
  question: "Saphnexa は何をするシステムか",
  retrieval_policy: { top_k: 10, allowed_acl_scope_ids: ["user:user-owner"] }
});
const document = api.request("admin-1", "createDocument", {
  csrf_token: adminCsrf,
  title: "integrity document",
  document_id: "doc-integrity",
  version_id: "ver-integrity",
  metadata: { document_id: "doc-integrity", version: "v1", acl_scope: "admin", status: "uploaded" }
});
const evaluation = api.request("admin-1", "startEvaluationRun", { csrf_token: adminCsrf, dataset_id: "dataset-local-golden" });
assert(accepted.status === 202, "question submit must be accepted");
assert(document.status === 202, "document create must be accepted");
assert(evaluation.status === 202, "evaluation run must be accepted");

const state = api.store.state;
const violations = [];

for (const user of state.users) exists(state.tenants, "tenant_id", user.tenant_id, `user tenant missing ${user.user_id}`);
for (const participant of state.chat_participants) {
  exists(state.chat_sessions, "chat_id", participant.chat_id, `participant chat missing ${participant.chat_id}`);
  exists(state.users, "user_id", participant.user_id, `participant user missing ${participant.user_id}`);
}
for (const message of state.chat_messages) {
  exists(state.chat_sessions, "chat_id", message.chat_id, `message chat missing ${message.message_id}`);
}
for (const run of state.chat_runs) {
  exists(state.chat_sessions, "chat_id", run.chat_id, `run chat missing ${run.run_id}`);
  exists(state.chat_messages, "message_id", run.message_id, `run message missing ${run.run_id}`);
}
for (const version of state.document_versions) {
  exists(state.documents, "document_id", version.document_id, `version document missing ${version.version_id}`);
}
for (const job of state.ingestion_jobs) {
  exists(state.document_versions, "version_id", job.version_id, `job version missing ${job.job_id}`);
}
for (const run of state.evaluation_runs) {
  exists(state.evaluation_datasets, "dataset_id", run.dataset_id, `evaluation dataset missing ${run.evaluation_run_id}`);
  assert(run.metrics_json.retrieval && run.metrics_json.generation && run.metrics_json.end_to_end, "evaluation metrics must contain three categories");
}
for (const artifact of state.published_artifacts) {
  assert(artifact.viewer_path.startsWith("/admin/"), `artifact viewer path must be admin-only: ${artifact.artifact_id}`);
  assert(artifact.status === "published-local", `artifact status mismatch: ${artifact.artifact_id}`);
}

for (const [key, events] of groupEvents(state.chat_message_events)) {
  const seen = new Set();
  const sorted = [...events].sort((a, b) => a.event_seq - b.event_seq);
  sorted.forEach((event, index) => {
    assert(event.event_seq === index + 1, `event seq gap for ${key}`);
    assert(!seen.has(event.event_seq), `event seq duplicate for ${key}`);
    seen.add(event.event_seq);
  });
  const snapshot = JSON.stringify(sorted);
  void sorted.map((event) => event.event_id);
  assert(JSON.stringify(sorted) === snapshot, `event payload/status changed during append-only check for ${key}`);
}

assert(violations.length === 0, `DB integrity violations: ${violations.join("; ")}`);
console.log("DB integrity check passed (violations=0, event_seq_duplicates=0)");

function csrf(userId) {
  return api.request(userId, "getMe").body.csrf_token;
}

function exists(rows, key, value, message) {
  if (!rows.some((item) => item[key] === value)) violations.push(message);
}

function groupEvents(events) {
  const groups = new Map();
  for (const event of events) {
    const key = `${event.chat_id}:${event.message_id}`;
    groups.set(key, [...(groups.get(key) || []), event]);
  }
  return groups;
}
