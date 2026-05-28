import { assert, listFiles, readText } from "./lib.js";

const files = listFiles(["apps/web/src"], (path) => path.endsWith(".tsx"));
assert(files.length >= 2, "web TSX files must exist");

let commonUiUsers = 0;
let componentCandidates = 0;
for (const file of files) {
  const body = readText(file);
  if (/export function [A-Z]/.test(body)) componentCandidates += 1;
  if (body.includes("../../../../packages/ui/src/components")) commonUiUsers += 1;
  assert(!/\sstyle=\{/.test(body), `${file} contains inline style prop`);
  assert(body.includes("<main"), `${file} must include a main landmark`);
  assert(!/<button(?![^>]*\stype=)/.test(body), `${file} contains button without explicit type`);
  if (file.includes("ChatApp")) {
    assert(body.includes("<nav") && body.includes("aria-label=\"チャット一覧\""), "ChatApp must expose labelled chat navigation");
    assert(body.includes("aria-label=\"質問\""), "ChatApp textarea must have an accessible label");
    assert(body.includes("<p role=\"status\">チャットはありません</p>"), "ChatApp must render an honest empty chat state");
    assert(body.includes("<p role=\"status\">イベントはありません</p>"), "ChatApp must render an honest empty event state");
  }
  if (file.includes("AdminApp")) {
    assert(body.includes("aria-label=\"管理操作\""), "AdminApp must label admin actions");
    assert(body.includes("aria-label=\"成果物\""), "AdminApp must label artifact panel");
    assert(body.includes("<p role=\"status\">成果物はありません</p>"), "AdminApp must render an honest empty artifact state");
  }
}

const componentsSource = readText("packages/ui/src/components.tsx");
assert(componentsSource.includes("aria-label={`状態: ${props.status}`}"), "StatusBadge must expose an accessible status label");

const usageRate = componentCandidates === 0 ? 0 : commonUiUsers / componentCandidates;
assert(usageRate >= 0.9, `common UI package usage below 90%: ${(usageRate * 100).toFixed(1)}%`);

console.log(`UI quality check passed (common_ui_usage=${(usageRate * 100).toFixed(1)}%, inline_style_violations=0)`);
