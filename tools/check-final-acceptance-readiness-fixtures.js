import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { requiredArtifactIds } from "./acceptance-artifact-summary.js";
import { acceptanceIds } from "./acceptance-ids.js";
import { requiredExternalActionIds } from "./external-acceptance-actions.js";
import { buildFinalAcceptanceReadiness } from "./final-acceptance-readiness.js";
import { assert, currentJstTimestamp } from "./lib.js";

const root = mkdtempSync(join(tmpdir(), "saphnexa-final-readiness-"));

try {
  const readiness = buildFinalAcceptanceReadiness(join(root, "final-readiness-ready.json"), {
    traceRows: acceptanceIds.map((id) => ({ id, state: "local_verified", evidence: "fixture final evidence" })),
    defectSnapshot: {
      blocker_critical_open_count: 0,
      captured_at: currentJstTimestamp(),
      source: "fixture"
    },
    externalActionPlan: buildCompletedExternalActionPlan(),
    finalCandidateStatus: {
      ready: true,
      status: "ready",
      missing_files: [],
      errors: []
    }
  });

  assert(readiness.final_acceptance_ready === true, "final readiness fixture must be ready");
  assert(readiness.readiness_reason.includes("aggregate release"), "final readiness ready reason missing");
  assert(readiness.blocking_acceptance_ids.length === 0, "final readiness fixture must have no blockers");
  assert(readiness.priority_gates.P0_all_pass === true, "final readiness fixture P0 gate must pass");
  assert(readiness.priority_gates.P1_all_pass === true, "final readiness fixture P1 gate must pass");
  assert(readiness.priority_gates.P2_all_pass === true, "final readiness fixture P2 gate must pass");
  assert(readiness.release_gate.ready === true && readiness.release_gate.pending.length === 0, "release gate must be ready");
  assert(readiness.aws_gate.ready === true && readiness.aws_gate.pending.length === 0, "AWS gate must be ready");
  assert(readiness.checklist_gate.ready === true && readiness.checklist_gate.pending_acceptance_ids.length === 0, "checklist gate must be ready");
  assert(readiness.checklist_gate.pending_result === "PASS", "checklist gate pending result must become PASS");
  assert(readiness.defect_gate.ready === true, "defect gate must be ready");
  assert(readiness.final_candidate_gate.ready === true, "final candidate gate must be ready");
  assert(readiness.final_candidate_gate.status === "ready", "final candidate gate status must be ready");
  assert(readiness.external_action_gate.ready === true, "external action gate must be ready");
  assert(readiness.external_action_gate.status === "completed_by_final_evidence", "external action gate ready status mismatch");
  assert(readiness.external_action_gate.pending_action_ids.length === 0, "external action gate must have no pending action ids");
  assert(readiness.external_action_gate.requires_confirmation === false, "completed external actions must not require confirmation");
  assert(readiness.artifact_summary_gate.ready === true, "artifact summary gate must be ready");
  assert(readiness.artifact_summary_gate.item_count === requiredArtifactIds.length, "artifact summary item count mismatch");
  assert(readiness.artifact_summary_gate.pending_external_count === 0, "artifact summary must have no pending external artifacts");
  assert(readiness.artifact_summary_gate.pending_action_ids.length === 0, "artifact summary must have no pending action ids");
  assert(readiness.artifact_summary_gate.final_ready_count > 0, "artifact summary must include final ready artifacts");

  const inconsistentFinalCandidateStatus = buildFinalAcceptanceReadiness(join(root, "final-readiness-inconsistent-candidate-status.json"), {
    traceRows: acceptanceIds.map((id) => ({ id, state: "local_verified", evidence: "fixture final evidence" })),
    defectSnapshot: {
      blocker_critical_open_count: 0,
      captured_at: currentJstTimestamp(),
      source: "fixture"
    },
    externalActionPlan: buildCompletedExternalActionPlan(),
    finalCandidateStatus: {
      ready: true,
      status: "invalid",
      missing_files: [],
      errors: ["fixture inconsistent final candidate error"]
    }
  });
  assert(inconsistentFinalCandidateStatus.final_acceptance_ready === false, "inconsistent final candidate status fixture must not be ready");
  assert(inconsistentFinalCandidateStatus.final_candidate_gate.ready === false, "inconsistent final candidate status gate must not be ready");
  assert(inconsistentFinalCandidateStatus.final_candidate_gate.status === "invalid", "inconsistent final candidate status must preserve status");
  assert(inconsistentFinalCandidateStatus.final_candidate_gate.errors.length > 0, "inconsistent final candidate errors must be explicit");

  const staleDefectSnapshot = buildFinalAcceptanceReadiness(join(root, "final-readiness-stale-defect-snapshot.json"), {
    traceRows: acceptanceIds.map((id) => ({ id, state: "local_verified", evidence: "fixture final evidence" })),
    defectSnapshot: {
      blocker_critical_open_count: 0,
      captured_at: "2026-05-27T18:53:00+09:00",
      source: "fixture"
    },
    externalActionPlan: buildCompletedExternalActionPlan(),
    finalCandidateStatus: {
      ready: true,
      status: "ready",
      missing_files: [],
      errors: []
    }
  });
  assert(staleDefectSnapshot.final_acceptance_ready === false, "stale defect snapshot fixture must not be ready");
  assert(staleDefectSnapshot.defect_gate.ready === false, "stale defect snapshot gate must not be ready");
  assert(staleDefectSnapshot.defect_gate.snapshot_fresh === false, "stale defect snapshot must not be fresh");
  assert(staleDefectSnapshot.defect_gate.pending.includes("fresh GitHub issue tracker snapshot"), "stale defect snapshot must require refresh");

  console.log("final acceptance readiness fixture check passed");
} finally {
  rmSync(root, { recursive: true, force: true });
}

function buildCompletedExternalActionPlan() {
  return {
    schema_version: "saphnexa-external-acceptance-action-plan.v1",
    generated_at: "2026-05-27T18:53:00+09:00",
    generated_by: "tools/check-final-acceptance-readiness-fixtures.js",
    ready: true,
    status: "completed_external_actions",
    blocking_acceptance_ids: [],
    actions: requiredExternalActionIds().map((id) => ({
      id,
      status: "completed",
      completed: true,
      requires_confirmation: true,
      external_state_change: true,
      candidate_commands: ["fixture command"],
      required_before_run: ["fixture prerequisite"],
      evidence_outputs: ["fixture evidence"],
      acceptance_ids: []
    })),
    pending_action_ids: [],
    note: "Fixture completed action plan for final readiness positive-path validation."
  };
}
