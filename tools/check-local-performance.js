import { performance } from "node:perf_hooks";
import { createLocalApi } from "../apps/api/src/local-api.js";
import { createLightweightNotification, assertNotificationIsLightweight } from "../apps/workers/src/event-publisher.js";
import { assert } from "./lib.js";

const api = createLocalApi();
const csrf_token = api.request("user-owner", "getMe").body.csrf_token;
const chat = api.request("user-owner", "createChatSession", { csrf_token, title: "perf" }).body.chat;
const durations = [];

for (let index = 0; index < 25; index += 1) {
  const start = performance.now();
  const response = api.request("user-owner", "submitQuestion", {
    csrf_token,
    chat_id: chat.chat_id,
    question: `Saphnexa は何をするシステムか ${index}`,
    retrieval_policy: { top_k: 10, allowed_acl_scope_ids: ["user:user-owner"] }
  });
  durations.push(performance.now() - start);
  assert(response.status === 202, "question submission must return accepted");
}

durations.sort((a, b) => a - b);
const p95 = durations[Math.floor(durations.length * 0.95) - 1];
assert(p95 <= 2000, `local question start p95 exceeded 2s: ${p95}`);

const lastEvent = api.store.state.chat_message_events.at(-1);
const notification = createLightweightNotification(lastEvent);
assert(assertNotificationIsLightweight(notification), "notification must stay lightweight");

console.log(`local performance check passed (question_start_p95_ms=${p95.toFixed(3)})`);
