import { cloudFormationInventoryPath } from "./cloudformation-inventory.js";
import { externalActionPlanPath } from "./external-acceptance-actions.js";
import { currentJstTimestamp } from "./lib.js";

export const artifactSummaryPath = "dist/acceptance/artifact_summary.draft.json";
const finalReadinessPath = "dist/acceptance/final_readiness.json";
export const requiredArtifactIds = [
  "source",
  "cdk-synth",
  "cloudformation-outputs",
  "db-migration",
  "allure-report",
  "docusaurus-docs",
  "ops-runbooks",
  "defect-list",
  "release",
  "final-checklist"
];

export function buildAcceptanceArtifactSummary({ gitCommit, finalReadinessReady, externalActionPlan }) {
  const externalPendingActionIds = finalReadinessReady ? [] : externalActionPlan.pending_action_ids;
  const externalArtifact = (status, pendingActionIds = []) => ({
    status: finalReadinessReady ? "final_ready" : status,
    pending_action_ids: finalReadinessReady ? [] : pendingActionIds
  });
  const artifacts = [
    artifact({
      id: "source",
      title: "Source repository snapshot",
      acceptance_ids: ["AC-002"],
      status: "local_ready",
      evidence: [`git_commit_sha:${gitCommit}`, "GitHub PR #1"],
      final_required: true
    }),
    artifact({
      id: "cdk-synth",
      title: "CDK synth result",
      acceptance_ids: ["AC-002", "AC-080", "AC-120"],
      status: "local_ready",
      evidence: ["npm run cdk:synth:local", ".github/workflows/ci.yml#cdk-synth"],
      final_required: true
    }),
    artifact({
      id: "cloudformation-outputs",
      title: "CloudFormation stack outputs and inventory",
      acceptance_ids: ["AC-002", "AC-081", "AC-150", "AC-151", "AC-152"],
      ...externalArtifact("pending_external", ["aws-deploy-publish", "cloudformation-capture"]),
      evidence: [cloudFormationInventoryPath, "docs/acceptance/cloudformation/cloudformation_inventory.uat.json"],
      final_required: true
    }),
    artifact({
      id: "db-migration",
      title: "DB migration result",
      acceptance_ids: ["AC-002", "AC-070", "AC-071"],
      status: "local_ready",
      evidence: ["npm run db:migration:check", "packages/db-migrations/migrations/V001__initial_saphnexa_schema.sql"],
      final_required: true
    }),
    artifact({
      id: "allure-report",
      title: "Allure test report",
      acceptance_ids: ["AC-002", "AC-021", "AC-088", "AC-121", "AC-126"],
      ...externalArtifact("local_ready", ["aws-deploy-publish"]),
      evidence: ["dist/admin/test-reports/allure/latest/", "npm run artifacts:check"],
      final_required: true
    }),
    artifact({
      id: "docusaurus-docs",
      title: "Docusaurus design documentation site",
      acceptance_ids: ["AC-002", "AC-020", "AC-087", "AC-143"],
      ...externalArtifact("local_ready", ["aws-deploy-publish"]),
      evidence: ["dist/admin/docs/latest/", "dist/admin/docs/versions/v0.16/", "npm run admin-artifacts:build"],
      final_required: true
    }),
    artifact({
      id: "ops-runbooks",
      title: "Operations runbooks",
      acceptance_ids: ["AC-002", "AC-143", "AC-144"],
      status: "local_ready",
      evidence: ["docs/ops/runbooks/", "npm run docs:check"],
      final_required: true
    }),
    artifact({
      id: "defect-list",
      title: "Fresh Blocker/Critical defect snapshot",
      acceptance_ids: ["AC-153", "AC-150", "AC-151", "AC-152"],
      ...externalArtifact("pending_external", ["defect-snapshot-refresh"]),
      evidence: ["docs/acceptance/defects/open_issues_snapshot.json", "dist/acceptance/defect_list.json"],
      final_required: true
    }),
    artifact({
      id: "release",
      title: "Git tag and GitHub release",
      acceptance_ids: ["AC-001", "AC-002", "AC-150", "AC-151", "AC-152"],
      ...externalArtifact("pending_external", ["release-tag", "github-release"]),
      evidence: ["Git tag", "GitHub release URL"],
      final_required: true
    }),
    artifact({
      id: "final-checklist",
      title: "Signed final acceptance checklist",
      acceptance_ids: ["AC-004", "AC-150", "AC-151", "AC-152", "AC-153"],
      ...externalArtifact("pending_external", ["final-evidence-candidate", "final-checklist-signoff"]),
      evidence: ["docs/acceptance/final/acceptance_checklist.csv"],
      final_required: true
    })
  ];

  return {
    schema_version: "saphnexa-acceptance-artifact-summary.v1",
    generated_at: currentJstTimestamp(),
    generated_by: "tools/build-acceptance-package.js",
    draft_status: "draft_not_for_final_acceptance",
    final_acceptance_ready: finalReadinessReady,
    final_readiness_path: finalReadinessPath,
    final_readiness_ready: finalReadinessReady,
    external_action_plan_path: externalActionPlanPath,
    external_actions_pending: externalPendingActionIds,
    artifacts,
    note: "Local draft summary for AC-002 deliverable tracking. Pending external artifacts require explicit confirmation and UAT evidence before final acceptance."
  };
}

export function summarizeAcceptanceArtifacts(artifactSummary) {
  return {
    path: artifactSummaryPath,
    item_count: artifactSummary.artifacts.length,
    local_ready_count: artifactSummary.artifacts.filter((item) => item.status === "local_ready").length,
    final_ready_count: artifactSummary.artifacts.filter((item) => item.status === "final_ready").length,
    pending_external_count: artifactSummary.artifacts.filter((item) => item.status === "pending_external").length,
    pending_action_ids: [...new Set(artifactSummary.artifacts.flatMap((item) => item.pending_action_ids))]
  };
}

function artifact(item) {
  return {
    pending_action_ids: [],
    ...item
  };
}
