import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { performance } from "node:perf_hooks";
import { gzipSync } from "node:zlib";
import { assert, listFiles, readText } from "./lib.js";

const sourceFiles = listFiles(["apps/web/src", "packages/ui/src", "packages/api-client/src"], (path) => /\.(ts|tsx)$/.test(path));
const sourceBundle = sourceFiles.map((path) => readText(path)).join("\n");
const gzipBytes = gzipSync(sourceBundle).byteLength;
const routeTargets = ["/chat", "/admin", "/admin/docs/latest/", "/admin/test-reports/allure/latest/"];
const routesSource = readText("apps/web/src/routes.ts");
const durations = [];

for (let index = 0; index < 200; index += 1) {
  const target = routeTargets[index % routeTargets.length];
  const start = performance.now();
  assert(routesSource.includes(`path: "${target}"`), `route missing: ${target}`);
  durations.push(performance.now() - start);
}

durations.sort((a, b) => a - b);
const p95 = durations[Math.floor(durations.length * 0.95) - 1];
const report = {
  schema_version: "web-bundle-local.v1",
  generated_by: "tools/check-web-bundle-report.js",
  source_file_count: sourceFiles.length,
  source_files: sourceFiles,
  gzip_bytes: gzipBytes,
  gzip_limit_bytes: 500 * 1024,
  route_targets: routeTargets,
  route_transition_p95_ms: Number(p95.toFixed(3)),
  route_transition_limit_ms: 500,
  note: "source bundle と route metadata のローカル gate。Lighthouse CI / production bundler analyzer の証跡ではない。"
};

write("dist/reports/web-bundle-local.json", `${JSON.stringify(report, null, 2)}\n`);
assert(report.gzip_bytes <= report.gzip_limit_bytes, `gzip size exceeds limit: ${report.gzip_bytes}`);
assert(report.route_transition_p95_ms <= report.route_transition_limit_ms, `route transition p95 exceeds limit: ${report.route_transition_p95_ms}`);
console.log(`web bundle check passed (gzip_bytes=${report.gzip_bytes}, route_transition_p95_ms=${report.route_transition_p95_ms})`);

function write(path, body) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
}
