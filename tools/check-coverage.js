import { spawnSync } from "node:child_process";
import { assert } from "./lib.js";

const result = spawnSync(process.execPath, [
  "--test",
  "--experimental-test-coverage",
  "--test-coverage-lines=80",
  "--test-coverage-branches=70",
  "tests/contract.test.js",
  "tests/e2e-local.test.js",
  "tests/integration-local.test.js"
], {
  stdio: "inherit"
});
assert(result.status === 0, "coverage thresholds failed: line >=80%, branch >=70%");

console.log("coverage check passed (line_threshold=80%, branch_threshold=70%)");
