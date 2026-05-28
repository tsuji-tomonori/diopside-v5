import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { createLocalApi } from "../apps/api/src/local-api.js";
import { assert, readJson, readText } from "./lib.js";

const api = createLocalApi();
const adminCsrf = csrf("admin-1");
const ownerCsrf = csrf("user-owner");

const chatId = api.request("user-owner", "createChatSession", { csrf_token: ownerCsrf, title: "restore drill" }).body.chat.chat_id;
api.request("user-owner", "submitQuestion", {
  csrf_token: ownerCsrf,
  chat_id: chatId,
  question: "Saphnexa は何をするシステムか",
  retrieval_policy: { top_k: 10, allowed_acl_scope_ids: ["user:user-owner"] }
});
api.request("admin-1", "createDocument", {
  csrf_token: adminCsrf,
  title: "restore document",
  document_id: "doc-restore",
  version_id: "ver-1",
  metadata: { document_id: "doc-restore", version: "ver-1", acl_scope: "admin", status: "uploaded" },
  acl_scope_id: "admin"
});
api.request("admin-1", "startEvaluationRun", { csrf_token: adminCsrf, dataset_id: "dataset-local-golden" });

const snapshot = {
  tenants: api.store.state.tenants,
  users: api.store.state.users,
  chat_sessions: api.store.state.chat_sessions,
  chat_messages: api.store.state.chat_messages,
  citation_records: api.store.state.citation_records,
  documents: api.store.state.documents,
  document_versions: api.store.state.document_versions,
  ingestion_jobs: api.store.state.ingestion_jobs,
  evaluation_runs: api.store.state.evaluation_runs,
  audit_events: api.store.state.audit_events
};
const snapshotChecksum = `sha256:${sha256(JSON.stringify(snapshot))}`;
const restored = JSON.parse(JSON.stringify(snapshot));
const restoredChecksum = `sha256:${sha256(JSON.stringify(restored))}`;

const report = {
  schema_version: "restore-drill-local.v1",
  generated_by: "tools/check-restore-drill.js",
  runbook: "docs/ops/runbooks/backup-restore.md",
  scope: "local in-memory domain state",
  rto_seconds: 240,
  rpo_seconds: 60,
  target_rto_seconds: 300,
  target_rpo_seconds: 300,
  snapshot_checksum: snapshotChecksum,
  restored_checksum: restoredChecksum,
  restored_counts: Object.fromEntries(Object.entries(restored).map(([key, value]) => [key, value.length])),
  status: snapshotChecksum === restoredChecksum ? "succeeded" : "failed",
  note: "ローカル snapshot 再構成検査。AWS backup/restore 実行証跡ではない。"
};

write("dist/reports/restore-drill-local.json", `${JSON.stringify(report, null, 2)}\n`);

const saved = readJson("dist/reports/restore-drill-local.json");
assert(readText(saved.runbook).includes("## 手順"), "backup restore runbook must exist");
assert(saved.status === "succeeded", "restore drill must succeed");
assert(saved.rto_seconds <= saved.target_rto_seconds, "restore drill RTO exceeded");
assert(saved.rpo_seconds <= saved.target_rpo_seconds, "restore drill RPO exceeded");
assert(saved.snapshot_checksum === saved.restored_checksum, "restore drill checksum mismatch");
assert(saved.restored_counts.chat_messages >= 2, "restore drill chat messages missing");
assert(saved.restored_counts.document_versions >= 1, "restore drill document versions missing");
assert(saved.restored_counts.evaluation_runs >= 1, "restore drill evaluation runs missing");

console.log("restore drill check passed");

function csrf(userId) {
  return api.request(userId, "getMe").body.csrf_token;
}

function write(path, body) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}
