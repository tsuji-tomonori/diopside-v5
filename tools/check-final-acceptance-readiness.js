import { existsSync } from "node:fs";
import { artifactSummaryPath, requiredArtifactIds } from "./acceptance-artifact-summary.js";
import { finalReadinessPath } from "./final-acceptance-readiness.js";
import { acceptanceCatalog, acceptanceCatalogPath, acceptanceIds } from "./acceptance-ids.js";
import { assert, isCurrentJstTimestamp, readJson, readText } from "./lib.js";

assert(existsSync(finalReadinessPath), `final readiness file missing: ${finalReadinessPath}`);

const readiness = readJson(finalReadinessPath);
const traceRows = parseTraceRows(readText("docs/acceptance/traceability.md"));
const unresolvedTraceIds = traceRows.filter((row) => row.state !== "local_verified").map((row) => row.id);
const blockingIds = readiness.blocking_acceptance_ids.map((row) => row.id);

assert(readiness.schema_version === "saphnexa-final-acceptance-readiness.v1", "final readiness schema version mismatch");
assert(isCurrentJstTimestamp(readiness.generated_at), "final readiness generated_at must be current JST timestamp");
assert(typeof readiness.final_acceptance_ready === "boolean", "final readiness must expose a boolean completion state");
assert(readiness.source_catalog.path === acceptanceCatalogPath, "final readiness source catalog path mismatch");
assert(readiness.source_catalog.item_count === acceptanceCatalog.item_count, "final readiness source catalog item count mismatch");
assert(JSON.stringify(readiness.source_catalog.priority_counts) === JSON.stringify(acceptanceCatalog.priority_counts), "final readiness source priority counts mismatch");
assert(readiness.artifact_summary_gate.status_path === artifactSummaryPath, "artifact summary gate path mismatch");
assert(readiness.artifact_summary_gate.item_count === requiredArtifactIds.length, "artifact summary gate item count mismatch");
assert(JSON.stringify(readiness.artifact_summary_gate.required_artifact_ids) === JSON.stringify(requiredArtifactIds), "artifact summary gate required ids mismatch");
assert(JSON.stringify(readiness.finalization_commands) === JSON.stringify([
  "npm run acceptance:external-actions:build",
  "npm run acceptance:external-actions:check",
  "CFN_CAPTURED_AT=<capture-iso-timestamp> npm run cfn:inventory:normalize",
  "gh issue list --state open --json number,title,labels,state",
  "npm run acceptance:final-manifest:build",
  "npm run acceptance:final-checklist:build",
  "npm run acceptance:final-candidate:fixture:check",
  "npm run acceptance:final:fixture:check",
  "npm run acceptance:final-candidate:check",
  "npm run acceptance:final:build",
  "npm run acceptance:final:check",
  "npm run acceptance:package:build",
  "npm run acceptance:package:check"
]), "finalization command order mismatch");
assert(
  readiness.finalization_commands.indexOf("CFN_CAPTURED_AT=<capture-iso-timestamp> npm run cfn:inventory:normalize") <
    readiness.finalization_commands.indexOf("npm run acceptance:final-manifest:build"),
  "finalization commands must normalize CloudFormation inventory before building manifest"
);
assert(
  readiness.finalization_commands.indexOf("gh issue list --state open --json number,title,labels,state") <
    readiness.finalization_commands.indexOf("npm run acceptance:final-manifest:build"),
  "finalization commands must refresh defect snapshot before building manifest"
);
assert(
  readiness.finalization_commands.indexOf("gh issue list --state open --json number,title,labels,state") <
    readiness.finalization_commands.indexOf("npm run acceptance:final-checklist:build"),
  "finalization commands must refresh defect snapshot before building checklist"
);
assert(
  readiness.finalization_commands.indexOf("npm run acceptance:final-manifest:build") <
    readiness.finalization_commands.indexOf("npm run acceptance:final-candidate:check"),
  "finalization commands must build manifest before checking final candidate"
);
assert(
  readiness.finalization_commands.indexOf("npm run acceptance:final-checklist:build") <
    readiness.finalization_commands.indexOf("npm run acceptance:final-candidate:check"),
  "finalization commands must build checklist before checking final candidate"
);

for (const id of unresolvedTraceIds) {
  assert(acceptanceIds.includes(id), `unknown acceptance id in trace: ${id}`);
  if (!readiness.final_acceptance_ready) assert(blockingIds.includes(id), `final readiness missing blocker ${id}`);
}
for (const id of blockingIds) {
  assert(unresolvedTraceIds.includes(id), `final readiness has stale blocker ${id}`);
}

if (readiness.final_acceptance_ready) {
  assert(readiness.trace_state_counts.requires_aws > 0, "final readiness must preserve source trace state counts");
  assert(readiness.blocking_acceptance_ids.length === 0, "final readiness ready state must have no blockers");
  assert(readiness.release_gate.ready === true && readiness.release_gate.pending.length === 0, "release gate must be ready");
  assert(readiness.aws_gate.ready === true && readiness.aws_gate.pending.length === 0, "AWS gate must be ready");
  assert(readiness.checklist_gate.ready === true && readiness.checklist_gate.pending_acceptance_ids.length === 0, "checklist gate must be ready");
  assert(readiness.checklist_gate.pending_result === "PASS", "checklist gate must be PASS");
  assert(readiness.defect_gate.ready === true, "defect gate must be ready");
  assert(readiness.defect_gate.blocker_critical_open_count === 0, "defect gate blocker/critical count must be 0");
  assert(readiness.defect_gate.snapshot_fresh === true, "defect gate must use a fresh snapshot");
  assert(readiness.defect_gate.snapshot_refresh_required === false, "defect gate must not require refresh");
  assert(readiness.defect_gate.pending.length === 0, "defect gate must not have pending reasons");
  assert(readiness.final_candidate_gate.ready === true, "final candidate gate must be ready");
  assert(readiness.final_candidate_gate.status === "ready", "final candidate status must be ready");
  assert(readiness.final_candidate_gate.missing_files.length === 0, "final candidate missing files must be empty");
  assert(readiness.final_candidate_gate.errors.length === 0, "final candidate errors must be empty");
  assert(readiness.external_action_gate.ready === true, "external action gate must be ready");
  assert(readiness.external_action_gate.status === "completed_by_final_evidence", "external action status must be completed by final evidence");
  assert(readiness.external_action_gate.pending_action_ids.length === 0, "external action pending ids must be empty");
  assert(readiness.external_action_gate.requires_confirmation === false, "completed external actions must not require confirmation");
  assert(readiness.artifact_summary_gate.ready === true, "artifact summary gate must be ready");
  assert(readiness.artifact_summary_gate.pending_external_count === 0, "artifact summary pending external count must be 0");
  assert(readiness.artifact_summary_gate.pending_action_ids.length === 0, "artifact summary pending action ids must be empty");
  assert(readiness.artifact_summary_gate.final_ready_count > 0, "artifact summary must include final ready items");
  assert(readiness.priority_gates.P0_all_pass === true, "P0 gate must pass");
  assert(readiness.priority_gates.P1_all_pass === true, "P1 gate must pass");
  assert(readiness.priority_gates.P2_all_pass === true, "P2 gate must pass");
  assert(readiness.note.includes("Final acceptance readiness is true"), "final readiness ready note missing");
} else {
  assert(readiness.trace_state_counts.requires_aws > 0, "final readiness must preserve AWS blockers");
  assert(readiness.release_gate.ready === false, "release gate must remain pending");
  assert(readiness.aws_gate.ready === false, "AWS gate must remain pending");
  assert(readiness.checklist_gate.ready === false, "checklist gate must remain pending");
  assert(readiness.defect_gate.ready === false, "defect gate must remain pending until final defect snapshot is refreshed");
  assert(readiness.defect_gate.blocker_critical_open_count === 0, "defect gate must preserve local blocker/critical open count");
  assert(readiness.defect_gate.snapshot_fresh === false, "local defect snapshot must not be treated as fresh final evidence");
  assert(readiness.defect_gate.snapshot_refresh_required === true, "defect gate must require final issue tracker refresh");
  assert(readiness.defect_gate.pending.includes("fresh GitHub issue tracker snapshot"), "defect gate must list fresh snapshot pending reason");
  assert(readiness.final_candidate_gate.ready === false, "final candidate gate must remain pending until final files exist");
  assert(readiness.final_candidate_gate.status === "not_ready", "final candidate status must be not_ready during local preflight");
  assert(readiness.final_candidate_gate.missing_files.length > 0, "final candidate missing files must be explicit");
  assert(readiness.external_action_gate.ready === false, "external action gate must remain pending");
  assert(readiness.external_action_gate.status === "pending_external_actions", "external action status mismatch");
  assert(readiness.external_action_gate.pending_action_ids.length > 0, "external action pending ids must be explicit");
  assert(readiness.external_action_gate.requires_confirmation === true, "external actions must require confirmation");
  assert(readiness.artifact_summary_gate.ready === false, "artifact summary gate must remain pending");
  assert(readiness.artifact_summary_gate.local_ready_count > 0, "artifact summary gate local ready count missing");
  assert(readiness.artifact_summary_gate.pending_external_count > 0, "artifact summary gate pending external count missing");
  assert(readiness.artifact_summary_gate.pending_action_ids.length > 0, "artifact summary gate pending actions missing");
  for (const actionId of readiness.artifact_summary_gate.pending_action_ids) {
    assert(readiness.external_action_gate.pending_action_ids.includes(actionId), `artifact summary pending action missing from external gate: ${actionId}`);
  }
  for (const id of ["AC-001", "AC-002", "AC-004", "AC-081", "AC-150", "AC-151", "AC-152", "AC-153"]) {
    assert(blockingIds.includes(id), `final readiness must keep ${id} pending`);
  }
  assert(readiness.priority_gates.P0_all_pass === false, "P0 gate must not pass");
  assert(readiness.priority_gates.P1_all_pass === false, "P1 gate must not pass");
  assert(readiness.priority_gates.P2_all_pass === true, "P2 gate should pass when no P2 blockers remain");
  assert(readiness.priority_gates.unresolved_by_priority.P0.includes("AC-150"), "AC-150 must remain a P0 aggregate blocker");
  assert(readiness.priority_gates.unresolved_by_priority.P0.includes("AC-151"), "AC-151 must remain a P0 aggregate blocker");
  assert(readiness.priority_gates.unresolved_by_priority.P0.includes("AC-153"), "AC-153 must remain a P0 defect snapshot blocker");
  assert(readiness.priority_gates.unresolved_by_priority.P1.includes("AC-152"), "AC-152 must remain a P1 aggregate blocker");
  assert(readiness.note.includes("must not be used as proof"), "final readiness limitation note missing");
}

for (const gate of [readiness.release_gate, readiness.aws_gate, readiness.checklist_gate]) {
  const pending = gate.pending || gate.pending_acceptance_ids || [];
  assert(readiness.final_acceptance_ready ? pending.length === 0 : pending.length > 0, "pending final evidence state mismatch");
}

console.log("final acceptance readiness check passed");

function parseTraceRows(body) {
  return [...body.matchAll(/^\| (AC-\d{3}) \| ([a-z_]+) \| (.+) \|$/gm)]
    .map((match) => ({ id: match[1], state: match[2], evidence: match[3] }));
}
