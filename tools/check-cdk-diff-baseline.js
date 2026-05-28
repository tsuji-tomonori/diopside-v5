import { readText, assert } from "./lib.js";

const baseline = readText("infra/aspects/security-baseline.js");
const required = ["Block Public Access", "SSE-KMS", "WAF", "wildcard", "retention"];
for (const token of required) {
  assert(baseline.toLowerCase().includes(token.toLowerCase()), `local CDK diff baseline missing ${token}`);
}

console.log("local CDK diff baseline check passed");
