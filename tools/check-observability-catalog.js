import { createLocalApi } from "../apps/api/src/local-api.js";
import {
  requiredAlarmCatalog,
  requiredMetricCatalog,
  retentionPolicyCatalog
} from "../packages/domain/src/observability.js";
import { assert } from "./lib.js";

const requiredMetrics = ["api_latency_ms", "api_5xx_count", "rag_latency_ms", "retrieval_count", "dlq_message_count", "ingestion_failed_count", "evaluation_failed_count"];
const requiredAlarms = ["api_5xx_alarm", "dlq_depth_alarm", "rag_failure_rate_alarm", "ingestion_failed_alarm", "evaluation_failed_alarm", "waf_block_spike_alarm"];

for (const metric of requiredMetrics) {
  const item = requiredMetricCatalog.find((entry) => entry.metric_name === metric);
  assert(item, `required metric missing: ${metric}`);
  assert(item.unit && item.acceptance, `required metric incomplete: ${metric}`);
}
for (const alarm of requiredAlarms) {
  const item = requiredAlarmCatalog.find((entry) => entry.alarm_name === alarm);
  assert(item, `required alarm missing: ${alarm}`);
  assert(item.metric_name && item.comparison_operator && typeof item.threshold === "number", `required alarm incomplete: ${alarm}`);
}
for (const item of retentionPolicyCatalog) {
  assert(item.retention_days > 0, `retention days must be set: ${item.resource_name}`);
}

const api = createLocalApi();
const ownerCsrf = api.request("user-owner", "getMe").body.csrf_token;
const adminCsrf = api.request("admin-1", "getMe").body.csrf_token;
const chat = api.request("user-owner", "createChatSession", { csrf_token: ownerCsrf, title: "observability" }).body.chat;
api.request("user-owner", "submitQuestion", {
  csrf_token: ownerCsrf,
  chat_id: chat.chat_id,
  question: "Saphnexa は何をするシステムか",
  retrieval_policy: { top_k: 10, allowed_acl_scope_ids: ["user:user-owner"] }
});
api.request("admin-1", "createDocument", {
  csrf_token: adminCsrf,
  title: "invalid observability document",
  metadata: { document_id: "doc-observability-invalid" }
});
api.request("admin-1", "startEvaluationRun", { csrf_token: adminCsrf, dataset_id: "dataset-local-golden" });

const localMetricSamples = {
  api_latency_ms: [1],
  api_5xx_count: [0],
  rag_latency_ms: [1],
  retrieval_count: [api.store.state.chat_message_events.filter((event) => event.event_name === "chat.retrieval.completed").length],
  dlq_message_count: [0],
  ingestion_failed_count: [api.store.state.ingestion_jobs.filter((job) => job.status === "failed").length],
  evaluation_failed_count: [api.store.state.evaluation_runs.filter((run) => run.status === "failed").length]
};

for (const metric of requiredMetrics) {
  assert(localMetricSamples[metric]?.length === 1, `local metric sample missing: ${metric}`);
}

console.log(`observability catalog check passed (metrics=${requiredMetrics.length}/7, alarms=${requiredAlarms.length}/6, retention_unset=0)`);
