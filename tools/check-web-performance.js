import { gzipSync } from "node:zlib";
import { performance } from "node:perf_hooks";
import { assert, listFiles, readText } from "./lib.js";

const sourceFiles = listFiles(["apps/web/src", "packages/ui/src", "packages/api-client/src"], (path) => /\.(ts|tsx)$/.test(path));
const sourceBundle = sourceFiles.map((path) => readText(path)).join("\n");
const gzipBytes = gzipSync(sourceBundle).byteLength;
assert(gzipBytes <= 500 * 1024, `web source gzip size exceeds 500KB: ${gzipBytes}`);

const targets = ["/chat", "/admin", "/admin/docs/latest/", "/admin/test-reports/allure/latest/"];
const routesSource = readText("apps/web/src/routes.ts");
const durations = [];
for (let index = 0; index < 100; index += 1) {
  const target = targets[index % targets.length];
  const start = performance.now();
  const routePattern = new RegExp(`path: "${escapeRegex(target)}".+role: "(admin|general_user)"`);
  assert(routePattern.test(routesSource), `route missing or role mismatch: ${target}`);
  durations.push(performance.now() - start);
}

durations.sort((a, b) => a - b);
const p95 = durations[Math.floor(durations.length * 0.95) - 1];
assert(p95 <= 500, `local route transition p95 exceeded 500ms: ${p95}`);

console.log(`web performance check passed (gzip_bytes=${gzipBytes}, route_transition_p95_ms=${p95.toFixed(3)})`);

function escapeRegex(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
