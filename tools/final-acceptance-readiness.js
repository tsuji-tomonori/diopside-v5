import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { buildAcceptanceArtifactSummary, summarizeAcceptanceArtifacts } from "./acceptance-artifact-summary.js";
import { acceptanceCatalog, acceptanceCatalogPath, priorityByAcceptanceId } from "./acceptance-ids.js";
import { buildExternalAcceptanceActionPlan, externalActionPlanPath } from "./external-acceptance-actions.js";
import { buildFinalEvidenceCandidateStatus, finalCandidateStatusPath } from "./final-evidence-candidate.js";
import { currentGitCommit } from "./git-context.js";
import { currentJstTimestamp, isCurrentJstTimestamp, readJson, readText } from "./lib.js";

export const finalReadinessPath = "dist/acceptance/final_readiness.json";

export function buildFinalAcceptanceReadiness(outputPath = finalReadinessPath, options = {}) {
  const traceRows = options.traceRows || parseTraceRows(readText("docs/acceptance/traceability.md"));
  const defectSnapshot = options.defectSnapshot || readJson("docs/acceptance/defects/open_issues_snapshot.json");
  const externalActionPlan = options.externalActionPlan || buildExternalAcceptanceActionPlan(externalActionPlanPath);
  const finalCandidateStatus = options.finalCandidateStatus || buildFinalEvidenceCandidateStatus(finalCandidateStatusPath);
  const finalCandidateReady = isFinalCandidateReady(finalCandidateStatus);
  const defectSnapshotFresh = isCurrentJstTimestamp(defectSnapshot.captured_at);
  const defectSnapshotRequiresRefresh = !defectSnapshotFresh || !finalCandidateReady;
  const defectGateReady = finalCandidateReady && defectSnapshot.blocker_critical_open_count === 0 && defectSnapshotFresh;
  const externalActionGateReady = (finalCandidateReady && defectGateReady) || externalActionPlan.ready === true;
  const aggregateEvidenceReady = finalCandidateReady && defectGateReady && externalActionGateReady;
  const artifactSummary = buildAcceptanceArtifactSummary({
    gitCommit: currentGitCommit(),
    finalReadinessReady: aggregateEvidenceReady,
    externalActionPlan
  });
  const artifactSummaryStats = summarizeAcceptanceArtifacts(artifactSummary);
  const traceBlockers = traceRows.filter((row) => row.state !== "local_verified");
  const blockers = (aggregateEvidenceReady ? [] : traceBlockers)
    .map((row) => ({
      id: row.id,
      priority: priorityByAcceptanceId[row.id] || "unknown",
      state: row.state,
      evidence: row.evidence
    }));
  const unresolvedByPriority = {
    P0: blockers.filter((row) => row.priority === "P0").map((row) => row.id),
    P1: blockers.filter((row) => row.priority === "P1").map((row) => row.id),
    P2: blockers.filter((row) => row.priority === "P2").map((row) => row.id)
  };
  const priorityGatesReady = unresolvedByPriority.P0.length === 0 && unresolvedByPriority.P1.length === 0 && unresolvedByPriority.P2.length === 0;
  const artifactSummaryReady = artifactSummaryStats.pending_external_count === 0 && artifactSummaryStats.pending_action_ids.length === 0;
  const finalAcceptanceReady = aggregateEvidenceReady && artifactSummaryReady && priorityGatesReady;

  const readiness = {
    schema_version: "saphnexa-final-acceptance-readiness.v1",
    generated_at: currentJstTimestamp(),
    generated_by: "tools/build-final-acceptance-readiness.js",
    final_acceptance_ready: finalAcceptanceReady,
    readiness_reason: finalAcceptanceReady
      ? "Final acceptance evidence candidate is ready and aggregate release, AWS, checklist, defect, and artifact gates are satisfied."
      : "Final acceptance still requires release, AWS/UAT, published artifact, CloudFormation, fresh defect snapshot, and signed checklist evidence.",
    source_catalog: {
      path: acceptanceCatalogPath,
      item_count: acceptanceCatalog.item_count,
      priority_counts: acceptanceCatalog.priority_counts
    },
    trace_state_counts: countStates(traceRows),
    blocking_acceptance_ids: blockers,
    priority_gates: {
      P0_all_pass: unresolvedByPriority.P0.length === 0,
      P1_all_pass: unresolvedByPriority.P1.length === 0,
      P2_all_pass: unresolvedByPriority.P2.length === 0,
      unresolved_by_priority: unresolvedByPriority
    },
    release_gate: {
      ready: finalCandidateReady,
      required_evidence: ["Git tag", "GitHub release", "final evidence_manifest.json"],
      pending: finalCandidateReady ? [] : ["Git tag", "GitHub release", "final evidence_manifest.json"]
    },
    aws_gate: {
      ready: finalCandidateReady,
      required_evidence: [
        "AWS account id",
        "deployed CloudFormation stack id",
        "CloudFormation describe-stacks",
        "CloudFormation list-stack-resources",
        "CloudFront/S3/Docusaurus/Allure published URLs"
      ],
      pending: finalCandidateReady ? [] : [
        "AWS account id",
        "deployed CloudFormation stack id",
        "CloudFormation describe-stacks",
        "CloudFormation list-stack-resources",
        "CloudFront/S3/Docusaurus/Allure published URLs"
      ]
    },
    checklist_gate: {
      ready: finalCandidateReady,
      required_evidence: ["final signed acceptance checklist"],
      pending_acceptance_ids: finalCandidateReady ? [] : blockers.map((row) => row.id),
      pending_result: finalCandidateReady ? "PASS" : "PENDING_AWS"
    },
    defect_gate: {
      ready: defectGateReady,
      blocker_critical_open_count: defectSnapshot.blocker_critical_open_count,
      source: defectSnapshot.source,
      captured_at: defectSnapshot.captured_at,
      snapshot_fresh: defectSnapshotFresh,
      snapshot_refresh_required: defectSnapshotRequiresRefresh,
      pending: defectGateReady ? [] : defectPendingReasons(defectSnapshot, defectSnapshotRequiresRefresh)
    },
    final_candidate_gate: {
      ready: finalCandidateReady,
      status_path: finalCandidateStatusPath,
      status: finalCandidateStatus.status,
      missing_files: finalCandidateStatus.missing_files,
      errors: finalCandidateStatus.errors
    },
    external_action_gate: {
      ready: externalActionGateReady,
      status_path: externalActionPlanPath,
      status: externalActionGateReady ? "completed_by_final_evidence" : externalActionPlan.status,
      pending_action_ids: externalActionGateReady ? [] : externalActionPlan.pending_action_ids,
      requires_confirmation: externalActionGateReady ? false : externalActionPlan.actions.every((action) => action.requires_confirmation)
    },
    artifact_summary_gate: {
      ready: artifactSummaryReady,
      status_path: artifactSummaryStats.path,
      item_count: artifactSummaryStats.item_count,
      local_ready_count: artifactSummaryStats.local_ready_count,
      final_ready_count: artifactSummaryStats.final_ready_count,
      pending_external_count: artifactSummaryStats.pending_external_count,
      pending_action_ids: artifactSummaryStats.pending_action_ids,
      required_artifact_ids: artifactSummary.artifacts.map((item) => item.id)
    },
    finalization_commands: [
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
    ],
    note: finalAcceptanceReady
      ? "Final acceptance readiness is true only because final candidate evidence, fresh defect snapshot, artifact, release, AWS, and checklist gates are satisfied."
      : "This readiness file is a preflight guard. It must not be used as proof that final acceptance is complete."
  };

  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, `${JSON.stringify(readiness, null, 2)}\n`);
  return readiness;
}

function isFinalCandidateReady(status) {
  return status?.ready === true && status.status === "ready" && empty(status.missing_files) && empty(status.errors);
}

function empty(value) {
  return Array.isArray(value) && value.length === 0;
}

function parseTraceRows(body) {
  return [...body.matchAll(/^\| (AC-\d{3}) \| ([a-z_]+) \| (.+) \|$/gm)]
    .map((match) => ({ id: match[1], state: match[2], evidence: match[3].replaceAll("`", "'") }));
}

function countStates(items) {
  const counts = { local_verified: 0, requires_aws: 0, implemented_unverified: 0, scaffolded: 0, not_started: 0 };
  for (const row of items) counts[row.state] = (counts[row.state] || 0) + 1;
  return counts;
}

function defectPendingReasons(defectSnapshot, requiresRefresh) {
  const pending = [];
  if (requiresRefresh) pending.push("fresh GitHub issue tracker snapshot");
  if (defectSnapshot.blocker_critical_open_count !== 0) pending.push("resolve Blocker/Critical defects");
  return pending;
}
