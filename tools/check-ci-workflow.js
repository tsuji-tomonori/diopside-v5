import { assert, readText } from "./lib.js";

const workflow = readText(".github/workflows/ci.yml");
const requiredJobs = [
  "lint",
  "typecheck",
  "unit",
  "integration",
  "e2e",
  "cdk-synth",
  "cdk-diff",
  "security-scan",
  "license-scan",
  "admin-artifacts",
  "quality-gates",
  "db-observability",
  "admin-offline-restore",
  "contract-generation-diff"
];

for (const job of requiredJobs) {
  assert(new RegExp(`^  ${job}:`, "m").test(workflow), `missing CI job ${job}`);
}

for (const command of [
  "npm run lint",
  "npm run typecheck",
  "npm test",
  "npm run test:integration:local",
  "npm run test:e2e:local",
  "npm run cdk:synth:local",
  "npm run cdk:diff:local",
  "npm run cfn:inventory:build",
  "npm run cfn:inventory:check",
  "npm run edge:security:check",
  "npm run security:scan",
  "npm run license:scan",
  "npm run admin-artifacts:build",
  "npm run artifacts:check",
  "npm run coverage:check",
  "npm run ui:check",
  "npm run web:flow:check",
  "npm run web:a11y:check",
  "npm run web:perf:local",
  "npm run web:bundle:check",
  "npm run perf:api:local",
  "npm run failure:check",
  "npm run rag:quality:check",
  "npm run rag:security:check",
  "npm run rag:perf:local",
  "npm run db:migration:check",
  "npm run db:integrity:check",
  "npm run search:local:check",
  "npm run observability:check",
  "npm run admin:workflow:check",
  "npm run offline-artifacts:check",
  "npm run restore:drill:check",
  "npm run test:contract",
  "npm run acceptance:source:check",
  "npm run acceptance:check",
  "npm run evidence:check",
  "npm run acceptance:external-actions:build",
  "npm run acceptance:external-actions:check",
  "npm run acceptance:final-candidate:check",
  "npm run acceptance:final-candidate:fixture:check",
  "npm run acceptance:final:fixture:check",
  "npm run acceptance:final:build",
  "npm run acceptance:final:check",
  "npm run acceptance:package:build",
  "npm run acceptance:package:check"
]) {
  assert(workflow.includes(command), `workflow missing command: ${command}`);
}

console.log("CI workflow check passed");
