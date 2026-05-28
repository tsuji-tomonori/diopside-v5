import { performance } from "node:perf_hooks";
import { createLocalApi } from "../apps/api/src/local-api.js";
import { assert } from "./lib.js";

const api = createLocalApi();
const ownerCsrf = api.request("user-owner", "getMe").body.csrf_token;
const adminCsrf = api.request("admin-1", "getMe").body.csrf_token;
const chat = api.request("user-owner", "createChatSession", { csrf_token: ownerCsrf, title: "api perf" }).body.chat;
const requests = [
  () => api.request("user-owner", "getMe"),
  () => api.request("user-owner", "listChatSessions"),
  () => api.request("user-owner", "getChatSession", { chat_id: chat.chat_id }),
  () => api.request("user-owner", "listFavorites"),
  () => api.request("user-owner", "listLlmModels"),
  () => api.request("admin-1", "adminListUsers"),
  () => api.request("admin-1", "listPublishedArtifacts"),
  () => api.request("admin-1", "issueArtifactAccessCookie", { csrf_token: adminCsrf })
];

const durations = [];
let errors = 0;
for (let index = 0; index < 160; index += 1) {
  const start = performance.now();
  const response = requests[index % requests.length]();
  durations.push(performance.now() - start);
  if (response.status >= 500) errors += 1;
}

durations.sort((a, b) => a - b);
const p95 = durations[Math.floor(durations.length * 0.95) - 1];
const errorRate = errors / durations.length;
assert(p95 <= 800, `local non-AI API p95 exceeded 800ms: ${p95}`);
assert(errorRate < 0.01, `local non-AI API error rate exceeded 1%: ${errorRate}`);

console.log(`local non-AI API performance check passed (p95_ms=${p95.toFixed(3)}, error_rate=${(errorRate * 100).toFixed(2)}%)`);
