import { pairwiseCases } from "../packages/testing/src/pairwise.js";
import { assert } from "./lib.js";

const expectedFactors = ["actor", "auth_state", "document_acl", "document_status", "response_mode", "channel_type", "input_type"];
assert(pairwiseCases.length === 15, `expected 15 pairwise cases, got ${pairwiseCases.length}`);
assert(new Set(pairwiseCases.map((item) => item.id)).size === 15, "pairwise IDs must be unique");

for (const testCase of pairwiseCases) {
  for (const factor of expectedFactors) {
    assert(Boolean(testCase[factor]), `${testCase.id} missing ${factor}`);
  }
  assert(Boolean(testCase.expected), `${testCase.id} missing expected result`);
}

const coverage = new Map();
for (const factor of expectedFactors) coverage.set(factor, new Set(pairwiseCases.map((item) => item[factor])));

assert(coverage.get("actor").size === 2, "actor factor must cover general user and admin");
assert(coverage.get("auth_state").size === 3, "auth_state factor must cover 3 states");
assert(coverage.get("document_acl").size === 3, "document_acl factor must cover 3 states");
assert(coverage.get("channel_type").size === 4, "channel_type factor must cover 4 channels");

console.log("pairwise check passed");
