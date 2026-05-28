import { createLocalApi } from "../apps/api/src/local-api.js";
import { assert } from "./lib.js";

const failureCases = [
  ["retrieval", "RAG_RETRIEVAL_FAILED"],
  ["generation", "RAG_GENERATION_FAILED"],
  ["worker_notify", "WORKER_NOTIFY_FAILED"]
];

for (const [failure_injection, expectedErrorCode] of failureCases) {
  const api = createLocalApi();
  const csrf_token = api.request("user-owner", "getMe").body.csrf_token;
  const chat = api.request("user-owner", "createChatSession", { csrf_token, title: `failure ${failure_injection}` }).body.chat;
  const accepted = api.request("user-owner", "submitQuestion", {
    csrf_token,
    chat_id: chat.chat_id,
    question: "Saphnexa は何をするシステムか",
    retrieval_policy: { top_k: 10, allowed_acl_scope_ids: ["user:user-owner"] },
    failure_injection
  });
  assert(accepted.status === 202, `${failure_injection} must still accept the run request`);
  const run = api.store.state.chat_runs.find((item) => item.run_id === accepted.body.run_id);
  const message = api.store.state.chat_messages.find((item) => item.message_id === accepted.body.message_id);
  const failedEvent = api.store.state.chat_message_events.find((item) => item.message_id === accepted.body.message_id && item.event_name === "chat.run.failed");
  assert(run.status === "failed", `${failure_injection} run must be failed`);
  assert(message.status === "failed", `${failure_injection} message must be failed`);
  assert(run.error_code === expectedErrorCode, `${failure_injection} error_code mismatch`);
  assert(run.retryable === true, `${failure_injection} run must be retryable`);
  assert(failedEvent?.payload_json?.error_code === expectedErrorCode, `${failure_injection} failed event error_code mismatch`);
  assert(failedEvent?.payload_json?.retryable === true, `${failure_injection} failed event must be retryable`);
}

console.log(`failure injection check passed (${failureCases.length}/3 cases)`);
