import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { assert, readText } from "./lib.js";

const checks = [];
checkFile("ChatApp", "apps/web/src/chat/ChatApp.tsx", [
  rule("main landmark", (body) => body.includes("<main className=\"sx-chat-shell\"")),
  rule("labelled navigation", (body) => body.includes("<nav aria-label=\"チャット一覧\">")),
  rule("question label", (body) => body.includes("aria-label=\"質問\"")),
  rule("question disabled state", (body) => body.includes("disabled={!csrfToken || !question}")),
  rule("event panel label", (body) => body.includes("aria-label=\"イベント\"")),
  rule("empty chat status", (body) => body.includes("<p role=\"status\">チャットはありません</p>")),
  rule("empty event status", (body) => body.includes("<p role=\"status\">イベントはありません</p>")),
  rule("button type", (body) => !/<button(?![^>]*\stype=)/.test(body))
]);
checkFile("AdminApp", "apps/web/src/admin/AdminApp.tsx", [
  rule("main landmark", (body) => body.includes("<main className=\"sx-admin-shell\"")),
  rule("admin action label", (body) => body.includes("aria-label=\"管理操作\"")),
  rule("artifact panel label", (body) => body.includes("aria-label=\"成果物\"")),
  rule("evaluation disabled state", (body) => body.includes("disabled={!csrfToken}")),
  rule("empty artifact status", (body) => body.includes("<p role=\"status\">成果物はありません</p>")),
  rule("artifact links from API data", (body) => body.includes("href={artifact.viewer_path}") && body.includes("{artifact.title}"))
]);
checkFile("UI components", "packages/ui/src/components.tsx", [
  rule("button type default", (body) => body.includes("type={props.type || \"button\"}")),
  rule("panel labelled section", (body) => body.includes("<section") && body.includes("aria-label={props[\"aria-label\"]}")),
  rule("status accessible name", (body) => body.includes("aria-label={`状態: ${props.status}`}"))
]);

const violations = checks.filter((item) => item.status === "failed");
const report = {
  schema_version: "web-a11y-local.v1",
  generated_by: "tools/check-web-accessibility-report.js",
  checks,
  violations: violations.length,
  note: "静的 source gate によるローカル a11y 検査。axe/Playwright の実 DOM report ではない。"
};
write("dist/reports/web-a11y-local.json", `${JSON.stringify(report, null, 2)}\n`);
assert(violations.length === 0, `web accessibility violations: ${violations.map((item) => item.name).join(", ")}`);
console.log(`web accessibility check passed (${checks.length} checks, violations=0)`);

function checkFile(label, path, rules) {
  const body = readText(path);
  for (const item of rules) {
    try {
      assert(item.predicate(body), `${label}: ${item.name}`);
      checks.push({ file: path, name: `${label}: ${item.name}`, status: "passed" });
    } catch (error) {
      checks.push({ file: path, name: `${label}: ${item.name}`, status: "failed", error: error.message });
    }
  }
}

function rule(name, predicate) {
  return { name, predicate };
}

function write(path, body) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
}
