import { performance } from "node:perf_hooks";
import { createLocalApi } from "../apps/api/src/local-api.js";
import { createLightweightNotification, assertNotificationIsLightweight } from "../apps/workers/src/event-publisher.js";
import { answerableGoldenCases } from "../packages/testing/src/rag-evaluation.js";
import { assert } from "./lib.js";

const api = createLocalApi();
const csrf_token = api.request("user-owner", "getMe").body.csrf_token;
const chat = api.request("user-owner", "createChatSession", { csrf_token, title: "rag timing" }).body.chat;
const firstEventDurations = [];
const finalDurations = [];
let timeouts = 0;

for (let index = 0; index < 30; index += 1) {
  const question = `${answerableGoldenCases[index % answerableGoldenCases.length].question} ${index}`;
  const start = performance.now();
  const accepted = api.request("user-owner", "submitQuestion", {
    csrf_token,
    chat_id: chat.chat_id,
    question,
    retrieval_policy: { top_k: 10, allowed_acl_scope_ids: ["user:user-owner"] }
  });
  assert(accepted.status === 202, "RAG question must be accepted");
  const events = api.store.state.chat_message_events.filter((event) => event.message_id === accepted.body.message_id);
  const firstEvent = events.find((event) => event.event_name === "chat.run.started" || event.event_type === "progress");
  const finalEvent = events.find((event) => event.event_name === "chat.message.final_ready");
  const end = performance.now();
  if (!firstEvent || !finalEvent) {
    timeouts += 1;
    continue;
  }
  firstEventDurations.push(end - start);
  finalDurations.push(end - start);
  assert(events.length <= 50, `RAG run emitted too many events: ${events.length}`);
  assert(assertNotificationIsLightweight(createLightweightNotification(finalEvent)), "final notification must be lightweight");
}

const timeoutRate = timeouts / 30;
const firstP95 = percentile(firstEventDurations, 0.95);
const finalP95 = percentile(finalDurations, 0.95);
assert(firstP95 <= 5000, `local RAG first notification p95 exceeded 5s: ${firstP95}`);
assert(finalP95 <= 60000, `local RAG final answer p95 exceeded 60s: ${finalP95}`);
assert(timeoutRate < 0.02, `local RAG timeout rate exceeded 2%: ${timeoutRate}`);

console.log(`RAG performance check passed (first_notification_p95_ms=${firstP95.toFixed(3)}, final_answer_p95_ms=${finalP95.toFixed(3)}, timeout_rate=${(timeoutRate * 100).toFixed(2)}%)`);

function percentile(values, ratio) {
  assert(values.length > 0, "no timing samples collected");
  return values.sort((a, b) => a - b)[Math.floor(values.length * ratio) - 1];
}
