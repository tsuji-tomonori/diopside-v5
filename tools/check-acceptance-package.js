import { existsSync } from "node:fs";
import { acceptanceCatalog, acceptanceCatalogPath, acceptanceIds, acceptanceItemById } from "./acceptance-ids.js";
import {
  assertSourceChecklistColumns,
  finalCheckedDateColumn,
  finalEvidenceColumn,
  finalResultColumn,
  finalReviewerColumn,
  sourceChecklistValue
} from "./acceptance-checklist-format.js";
import { currentGitCommit } from "./git-context.js";
import { assert, isCurrentJstDate, isCurrentJstTimestamp, readJson, readText } from "./lib.js";

const summary = readJson("dist/acceptance/summary.json");
const finalReady = summary.final_acceptance_ready === true;
const evidenceManifestPath = summary.evidence_manifest_path || "dist/acceptance/evidence_manifest.draft.json";
const manifest = readJson(evidenceManifestPath);
const artifactSummary = readJson("dist/acceptance/artifact_summary.draft.json");
const defects = readJson("dist/acceptance/defect_list.json");
const packageJson = readJson("package.json");
const checklist = readText("dist/acceptance/acceptance_checklist.draft.csv");
const currentCommit = currentGitCommit();

for (const path of [
  evidenceManifestPath,
  "dist/acceptance/evidence_manifest.draft.json",
  "dist/acceptance/artifact_summary.draft.json",
  "dist/acceptance/acceptance_checklist.draft.csv",
  "dist/acceptance/cloudformation_inventory.draft.json",
  "dist/acceptance/final_readiness.json",
  "dist/acceptance/final_candidate_status.json",
  "dist/acceptance/external_action_plan.json",
  "dist/acceptance/defect_list.json",
  "dist/acceptance/summary.json"
]) {
  assert(existsSync(path), `acceptance package file missing: ${path}`);
}

for (const key of ["system", "environment", "aws_region", "aws_account_id", "git_commit_sha", "git_tag", "github_release_url", "cdk_app_version", "cloudformation_stacks", "db_migration", "test_reports", "docs_site", "rag_evaluation", "cost_estimate"]) {
  assert(Object.prototype.hasOwnProperty.call(manifest, key), `manifest missing ${key}`);
}
assert(manifest.system === "Saphnexa", "manifest system mismatch");
assert(manifest.aws_region === "ap-northeast-1", "manifest region mismatch");
assert(/^[a-f0-9]{40}$/.test(manifest.git_commit_sha), "manifest git commit must be 40 hex chars");
assert(manifest.git_commit_sha === currentCommit, "manifest git commit must match current Git ref");
if (finalReady) {
  assert(evidenceManifestPath === "dist/acceptance/evidence_manifest.json", "final package must use final evidence manifest path");
  assert(!Object.prototype.hasOwnProperty.call(manifest, "draft_status"), "final manifest must not include draft_status");
  assert(!Object.prototype.hasOwnProperty.call(manifest, "pending_final_evidence"), "final manifest must not include pending_final_evidence");
  assert(/^[0-9]{12}$/.test(manifest.aws_account_id), "final manifest must include a real AWS account id");
  assert(isFinalText(manifest.git_tag), "final manifest must include a final Git tag");
  assert(isGitHubReleaseUrlForTag(manifest.github_release_url, manifest.git_tag), "final manifest release URL must match git_tag");
} else {
  assert(evidenceManifestPath === "dist/acceptance/evidence_manifest.draft.json", "draft package must use draft evidence manifest path");
  assert(manifest.draft_status === "draft_not_for_final_acceptance", "manifest must be marked as draft");
  assert(manifest.pending_final_evidence.length >= 5, "manifest pending final evidence must be explicit");
  assert(manifest.aws_account_id === "pending-aws-account-id", "draft manifest must not pretend to know AWS account id");
  assert(manifest.git_tag === "pending-release-tag", "draft manifest must not pretend release tag is created");
  assert(manifest.github_release_url === "pending-github-release-url", "draft manifest must not pretend GitHub release is created");
}
assert(manifest.cdk_app_version === packageJson.version, "draft manifest CDK app version must match package version");
if (!finalReady) {
  assert(manifest.cloudformation_inventory.draft_path === "dist/acceptance/cloudformation_inventory.draft.json", "manifest CloudFormation inventory path mismatch");
  assert(manifest.cloudformation_inventory.final_acceptance_eligible === false, "manifest CloudFormation inventory must be draft-only");
  assert(manifest.cloudformation_inventory.aws_capture_required === true, "manifest CloudFormation inventory must require AWS capture");
  assert(manifest.artifact_summary.draft_path === "dist/acceptance/artifact_summary.draft.json", "manifest artifact summary path mismatch");
  assert(manifest.artifact_summary.item_count >= 8, "manifest artifact summary item count too small");
  assert(manifest.artifact_summary.pending_external_count > 0, "manifest artifact summary pending external state mismatch");
  assert(manifest.source_catalog.path === acceptanceCatalogPath, "manifest source catalog path mismatch");
  assert(manifest.source_catalog.item_count === acceptanceCatalog.item_count, "manifest source catalog item count mismatch");
  assert(JSON.stringify(manifest.source_catalog.priority_counts) === JSON.stringify(acceptanceCatalog.priority_counts), "manifest source priority counts mismatch");
  assert(manifest.final_readiness.path === "dist/acceptance/final_readiness.json", "manifest final readiness path mismatch");
  assert(manifest.final_readiness.final_acceptance_ready === false, "manifest final readiness state mismatch");
  assert(manifest.final_readiness.blocking_acceptance_ids.length > 0, "manifest final readiness blockers state mismatch");
  assert(manifest.final_readiness.release_gate_ready === false, "manifest release gate state mismatch");
  assert(manifest.final_readiness.aws_gate_ready === false, "manifest AWS gate state mismatch");
  assert(manifest.final_readiness.checklist_gate_ready === false, "manifest checklist gate state mismatch");
  assert(manifest.final_readiness.final_candidate_status_path === "dist/acceptance/final_candidate_status.json", "manifest final candidate status path mismatch");
  assert(manifest.final_readiness.final_candidate_ready === false, "manifest final candidate state mismatch");
  assert(manifest.final_readiness.external_action_plan_path === "dist/acceptance/external_action_plan.json", "manifest external action plan path mismatch");
  assert(manifest.final_readiness.external_actions_pending.length > 0, "manifest external pending actions state mismatch");
}

const rows = parseCsv(checklist);
assertSourceChecklistColumns(rows.headers, assert);
assert(rows.length === acceptanceIds.length, `checklist row count mismatch: ${rows.length}`);
for (const id of acceptanceIds) {
  assert(rows.some((row) => row.ID === id), `checklist missing ${id}`);
}
for (const row of rows) {
  for (const key of ["ID", "state", finalResultColumn, finalEvidenceColumn, finalReviewerColumn, finalCheckedDateColumn, "備考"]) {
    assert(String(row[key] || "").length > 0, `checklist ${row.ID} has empty ${key}`);
  }
  const source = acceptanceItemById[row.ID];
  assert(row["領域"] === source.area, `${row.ID} checklist area must match source catalog`);
  assert(row["重要度"] === source.priority, `${row.ID} checklist priority must match source catalog`);
  assert(row["検収項目"] === source.item, `${row.ID} checklist item must match source catalog`);
  assert(row["受け入れ条件 / 完了条件"] === source.acceptance_condition, `${row.ID} checklist condition must match source catalog`);
  if (row.state === "requires_aws") {
    assert(sourceChecklistValue(row, finalResultColumn) === "PENDING_AWS", `${row.ID} requires_aws must remain PENDING_AWS`);
  }
  if (sourceChecklistValue(row, finalResultColumn) === "PASS_LOCAL") {
    assert(row.state === "local_verified", `${row.ID} PASS_LOCAL must map to local_verified`);
  }
  assert(isCurrentJstDate(sourceChecklistValue(row, finalCheckedDateColumn)), `${row.ID} checklist checked date must be current JST date`);
}

assert(defects.blocker_critical_open_count === 0, "blocker/critical defects must be 0 in snapshot");
assert(Array.isArray(defects.open_issues), "defect snapshot open_issues must be an array");
assert(isCurrentJstTimestamp(summary.generated_at), "summary generated_at must be current JST timestamp");
assert(summary.git_commit_sha === currentCommit, "summary git commit must match current Git ref");
assert(summary.git_commit_sha === manifest.git_commit_sha, "summary git commit must match manifest git commit");
assert(summary.evidence_manifest_path === evidenceManifestPath, "summary evidence manifest path mismatch");
assert(summary.checklist_rows === acceptanceIds.length, "summary checklist row count mismatch");
assert(summary.source_catalog_path === acceptanceCatalogPath, "summary source catalog path mismatch");
assert(summary.source_catalog_items === acceptanceCatalog.item_count, "summary source catalog item count mismatch");
assert(JSON.stringify(summary.source_priority_counts) === JSON.stringify(acceptanceCatalog.priority_counts), "summary source priority counts mismatch");
assert(summary.cloudformation_inventory_draft_path === "dist/acceptance/cloudformation_inventory.draft.json", "summary CloudFormation inventory path mismatch");
assert(summary.artifact_summary_draft_path === "dist/acceptance/artifact_summary.draft.json", "summary artifact path mismatch");
assert(summary.artifact_summary_items === artifactSummary.artifacts.length, "summary artifact count mismatch");
assert(
  finalReady ? summary.artifact_summary_pending_external === 0 : summary.artifact_summary_pending_external > 0,
  "summary artifact pending external state mismatch"
);
assert(summary.final_readiness_path === "dist/acceptance/final_readiness.json", "summary final readiness path mismatch");
assert(summary.final_readiness_ready === finalReady, "summary final readiness state mismatch");
assert(summary.final_candidate_status_path === "dist/acceptance/final_candidate_status.json", "summary final candidate path mismatch");
assert(summary.final_candidate_ready === finalReady, "summary final candidate state mismatch");
assert(summary.external_action_plan_path === "dist/acceptance/external_action_plan.json", "summary external action plan path mismatch");
assert(finalReady ? summary.external_actions_pending === 0 : summary.external_actions_pending > 0, "summary external action pending state mismatch");
assert(finalReady ? summary.trace_state_counts.requires_aws === 0 : summary.trace_state_counts.requires_aws > 0, "summary trace state mismatch");
assert(summary.final_acceptance_ready === finalReady, "summary final acceptance readiness mismatch");

assert(artifactSummary.schema_version === "saphnexa-acceptance-artifact-summary.v1", "artifact summary schema mismatch");
assert(isCurrentJstTimestamp(artifactSummary.generated_at), "artifact summary generated_at must be current JST timestamp");
assert(artifactSummary.draft_status === "draft_not_for_final_acceptance", "artifact summary must be draft-only");
assert(artifactSummary.final_acceptance_ready === finalReady, "artifact summary final acceptance readiness mismatch");
assert(artifactSummary.final_readiness_path === "dist/acceptance/final_readiness.json", "artifact summary final readiness path mismatch");
assert(artifactSummary.final_readiness_ready === finalReady, "artifact summary final readiness state mismatch");
assert(artifactSummary.external_action_plan_path === "dist/acceptance/external_action_plan.json", "artifact summary external action path mismatch");
assert(JSON.stringify(artifactSummary.external_actions_pending) === JSON.stringify(manifest.final_readiness.external_actions_pending), "artifact summary external pending actions mismatch");

for (const id of ["source", "cdk-synth", "cloudformation-outputs", "db-migration", "allure-report", "docusaurus-docs", "ops-runbooks", "defect-list", "release", "final-checklist"]) {
  assert(artifactSummary.artifacts.some((item) => item.id === id), `artifact summary missing ${id}`);
}
for (const item of artifactSummary.artifacts) {
  assert(item.final_required === true, `${item.id} must be marked final required`);
  assert(["local_ready", "pending_external", "final_ready"].includes(item.status), `${item.id} status mismatch`);
  assert(Array.isArray(item.acceptance_ids) && item.acceptance_ids.length > 0, `${item.id} acceptance ids missing`);
  assert(Array.isArray(item.evidence) && item.evidence.length > 0, `${item.id} evidence missing`);
  assert(Array.isArray(item.pending_action_ids), `${item.id} pending action ids missing`);
  if (item.status === "pending_external") {
    assert(item.pending_action_ids.length > 0, `${item.id} pending external item must list actions`);
  }
}
assert(
  artifactSummary.artifacts.some((item) => item.id === "cloudformation-outputs" && item.status === (finalReady ? "final_ready" : "pending_external")),
  "CloudFormation outputs state mismatch"
);
assert(
  artifactSummary.artifacts.some((item) => item.id === "defect-list" && item.status === (finalReady ? "final_ready" : "pending_external")),
  "defect list state mismatch"
);
assert(
  artifactSummary.artifacts.some((item) => item.id === "release" && item.status === (finalReady ? "final_ready" : "pending_external")),
  "release artifacts state mismatch"
);
assert(
  artifactSummary.artifacts.some((item) => item.id === "final-checklist" && item.status === (finalReady ? "final_ready" : "pending_external")),
  "final checklist state mismatch"
);
assert(artifactSummary.artifacts.some((item) => item.id === "final-checklist" && item.acceptance_ids.includes("AC-153")), "final checklist artifact must cover AC-153 signoff");
assert(artifactSummary.artifacts.every((item) => item.status !== "complete"), "artifact summary must not use ambiguous complete status");

console.log("acceptance package check passed");

function parseCsv(body) {
  const lines = body.trim().split(/\r?\n/);
  const headers = splitCsvLine(lines[0]);
  const rows = lines.slice(1).map((line) => Object.fromEntries(splitCsvLine(line).map((value, index) => [headers[index], value])));
  rows.headers = headers;
  return rows;
}

function splitCsvLine(line) {
  const values = [];
  let current = "";
  let quoted = false;
  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    if (char === '"' && quoted && line[index + 1] === '"') {
      current += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      values.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  values.push(current);
  return values;
}

function isFinalText(value) {
  return typeof value === "string" && value.trim().length > 0 && !/pending|example|draft|placeholder|not-for-acceptance/i.test(value);
}

function isGitHubReleaseUrlForTag(value, gitTag) {
  try {
    const url = new URL(value);
    const match = url.pathname.match(/^\/[^/]+\/[^/]+\/releases\/tag\/(.+)$/);
    return url.protocol === "https:" && url.hostname === "github.com" && decodeURIComponent(match?.[1] || "") === gitTag;
  } catch {
    return false;
  }
}
