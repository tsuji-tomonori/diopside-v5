import { existsSync } from "node:fs";
import { externalActionPlanPath, requiredExternalActionIds } from "./external-acceptance-actions.js";
import { assert, isCurrentJstTimestamp, readJson, readText } from "./lib.js";

assert(existsSync(externalActionPlanPath), `external action plan missing: ${externalActionPlanPath}`);

const plan = readJson(externalActionPlanPath);
const unresolvedTraceIds = parseTraceRows(readText("docs/acceptance/traceability.md"))
  .filter((row) => row.state !== "local_verified")
  .map((row) => row.id);

assert(plan.schema_version === "saphnexa-external-acceptance-action-plan.v1", "external action plan schema mismatch");
assert(isCurrentJstTimestamp(plan.generated_at), "external action plan generated_at must be current JST timestamp");
assert(plan.ready === false, "external action plan must remain not ready until actions are completed");
assert(plan.status === "pending_external_actions", "external action plan status mismatch");

for (const id of requiredExternalActionIds()) {
  assert(plan.actions.some((action) => action.id === id), `missing external action ${id}`);
}
for (const id of unresolvedTraceIds) {
  assert(plan.blocking_acceptance_ids.includes(id), `external action plan missing blocker ${id}`);
  assert(plan.actions.some((action) => action.acceptance_ids.includes(id)), `no external action covers ${id}`);
}
for (const action of plan.actions) {
  assert(action.status === "pending", `${action.id} must remain pending`);
  assert(action.completed === false, `${action.id} must not be completed by preflight`);
  assert(action.requires_confirmation === true, `${action.id} must require confirmation`);
  assert(action.external_state_change === true, `${action.id} must be marked as external state change`);
  assert(action.candidate_commands.length > 0, `${action.id} must list candidate commands`);
  assert(action.required_before_run.length > 0, `${action.id} must list prerequisites`);
  assert(action.evidence_outputs.length > 0, `${action.id} must list evidence outputs`);
}
const awsDeployPublish = plan.actions.find((action) => action.id === "aws-deploy-publish");
assert(awsDeployPublish.candidate_commands.includes("aws s3 sync dist/admin/docs/latest/ s3://<admin-artifacts-bucket>/docs-site/latest/"), "docs latest publish command must use design docs-site/latest prefix");
assert(awsDeployPublish.candidate_commands.includes("aws s3 sync dist/admin/docs/versions/v0.16/ s3://<admin-artifacts-bucket>/docs-site/releases/v0.16/"), "docs version publish command must use design docs-site/releases/v0.16 prefix");
assert(!awsDeployPublish.candidate_commands.includes("aws s3 sync dist/admin/docs/ s3://<admin-artifacts-bucket>/docs/"), "docs publish command must not use legacy docs/ prefix");
const cloudFormationCapture = plan.actions.find((action) => action.id === "cloudformation-capture");
assert(cloudFormationCapture.candidate_commands.includes("CFN_CAPTURED_AT=<capture-iso-timestamp> npm run cfn:inventory:normalize"), "CloudFormation capture action must include final inventory normalizer command");
const defectSnapshotRefresh = plan.actions.find((action) => action.id === "defect-snapshot-refresh");
assert(defectSnapshotRefresh.acceptance_ids.includes("AC-153"), "defect snapshot refresh action must cover AC-153");
assert(defectSnapshotRefresh.candidate_commands.includes("gh issue list --state open --json number,title,labels,state"), "defect snapshot refresh action must include GitHub issue list command");
assert(defectSnapshotRefresh.evidence_outputs.includes("docs/acceptance/defects/open_issues_snapshot.json"), "defect snapshot refresh action must output defect snapshot");
const finalEvidenceCandidate = plan.actions.find((action) => action.id === "final-evidence-candidate");
assert(finalEvidenceCandidate.acceptance_ids.includes("AC-153"), "final evidence candidate action must include AC-153");
assert(finalEvidenceCandidate.required_before_run.includes("fresh defect snapshot"), "final evidence candidate action must require fresh defect snapshot");
assert(finalEvidenceCandidate.candidate_commands.includes("npm run acceptance:final-manifest:build"), "final evidence candidate action must include manifest builder command");
assert(finalEvidenceCandidate.candidate_commands.includes("npm run acceptance:final-checklist:build"), "final evidence candidate action must include checklist builder command");
assert(
  finalEvidenceCandidate.candidate_commands.indexOf("npm run acceptance:final-manifest:build") <
    finalEvidenceCandidate.candidate_commands.indexOf("npm run acceptance:final-candidate:check"),
  "final evidence candidate action must build manifest before checking candidate"
);
assert(
  finalEvidenceCandidate.candidate_commands.indexOf("npm run acceptance:final-checklist:build") <
    finalEvidenceCandidate.candidate_commands.indexOf("npm run acceptance:final-candidate:check"),
  "final evidence candidate action must build checklist before checking candidate"
);
assert(plan.pending_action_ids.length === plan.actions.length, "all actions must be pending before external execution");
assert(plan.note.includes("require explicit confirmation"), "external action confirmation note missing");

console.log("external acceptance action plan check passed");

function parseTraceRows(body) {
  return [...body.matchAll(/^\| (AC-\d{3}) \| ([a-z_]+) \| (.+) \|$/gm)]
    .map((match) => ({ id: match[1], state: match[2], evidence: match[3] }));
}
