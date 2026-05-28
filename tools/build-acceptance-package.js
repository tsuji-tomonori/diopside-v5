import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { artifactSummaryPath, buildAcceptanceArtifactSummary, summarizeAcceptanceArtifacts } from "./acceptance-artifact-summary.js";
import { acceptanceCatalog, acceptanceCatalogPath, acceptanceIds, acceptanceItemById } from "./acceptance-ids.js";
import { sourceChecklistColumns } from "./acceptance-checklist-format.js";
import { buildCloudFormationInventoryDraft, cloudFormationInventoryPath } from "./cloudformation-inventory.js";
import { buildExternalAcceptanceActionPlan, externalActionPlanPath } from "./external-acceptance-actions.js";
import { buildFinalAcceptanceReadiness, finalReadinessPath } from "./final-acceptance-readiness.js";
import { currentGitCommit } from "./git-context.js";
import { currentJstDate, currentJstTimestamp, readJson, readText } from "./lib.js";

const outputRoot = "dist/acceptance";
const draftEvidenceManifestPath = join(outputRoot, "evidence_manifest.draft.json");
const finalEvidenceManifestSourcePath = "docs/acceptance/final/evidence_manifest.json";
const finalEvidenceManifestPackagePath = join(outputRoot, "evidence_manifest.json");
const trace = readText("docs/acceptance/traceability.md");
const packageJson = readJson("package.json");
const defectSnapshot = readJson("docs/acceptance/defects/open_issues_snapshot.json");
const gitCommit = currentGitCommit();
const generatedAt = currentJstTimestamp();
const generatedDate = currentJstDate();
const rows = parseTraceRows(trace);
const counts = countStates(rows);
const cloudFormationInventory = buildCloudFormationInventoryDraft(cloudFormationInventoryPath);
const externalActionPlan = buildExternalAcceptanceActionPlan(externalActionPlanPath);
const finalReadiness = buildFinalAcceptanceReadiness(finalReadinessPath);
const finalAcceptanceReady = finalReadiness.final_acceptance_ready;
const finalEvidenceManifest = finalAcceptanceReady ? readJson(finalEvidenceManifestSourcePath) : null;
const evidenceManifestPackagePath = finalAcceptanceReady ? finalEvidenceManifestPackagePath : draftEvidenceManifestPath;
const effectiveCounts = finalAcceptanceReady
  ? { local_verified: acceptanceIds.length, requires_aws: 0, implemented_unverified: 0, scaffolded: 0, not_started: 0 }
  : counts;
const artifactSummary = buildAcceptanceArtifactSummary({
  gitCommit,
  finalReadinessReady: finalAcceptanceReady,
  externalActionPlan
});
const artifactSummaryStats = summarizeAcceptanceArtifacts(artifactSummary);

const manifest = {
  system: "Saphnexa",
  environment: "uat",
  aws_region: "ap-northeast-1",
  aws_account_id: "pending-aws-account-id",
  git_commit_sha: gitCommit,
  git_tag: "pending-release-tag",
  github_release_url: "pending-github-release-url",
  cdk_app_version: packageJson.version,
  cloudformation_stacks: [
    {
      stack_name: "saphnexa-uat-app",
      stack_id: "pending-aws-cloudformation-deploy"
    }
  ],
  cloudformation_inventory: {
    draft_path: cloudFormationInventoryPath,
    schema_path: "docs/acceptance/cloudformation/cloudformation_inventory.schema.json",
    source: cloudFormationInventory.source,
    final_acceptance_eligible: cloudFormationInventory.final_acceptance_eligible,
    aws_capture_required: cloudFormationInventory.aws_capture_required
  },
  artifact_summary: {
    draft_path: artifactSummaryStats.path,
    item_count: artifactSummaryStats.item_count,
    local_ready_count: artifactSummaryStats.local_ready_count,
    pending_external_count: artifactSummaryStats.pending_external_count
  },
  db_migration: {
    tool: "Flyway",
    latest_version: "V001",
    checksum_status: "matched"
  },
  test_reports: {
    allure_latest_url: "dist/admin/test-reports/allure/latest/",
    unit_report_url: "dist/admin/test-reports/allure/latest/",
    integration_report_url: "dist/admin/test-reports/allure/latest/",
    e2e_report_url: "dist/admin/test-reports/allure/latest/"
  },
  docs_site: {
    latest_url: "dist/admin/docs/latest/",
    version_url: "dist/admin/docs/versions/v0.16/"
  },
  rag_evaluation: {
    evaluation_run_id: "local-rag-quality-report",
    report_url: "dist/reports/rag-quality-local.json"
  },
  cost_estimate: {
    monthly_usd: 550,
    assumption: "Local acceptance draft uses the configured 50 DAU / 10 questions per user per day guardrail. Final UAT requires AWS account-specific cost evidence."
  },
  final_readiness: {
    path: finalReadinessPath,
    final_acceptance_ready: finalReadiness.final_acceptance_ready,
    blocking_acceptance_ids: finalReadiness.blocking_acceptance_ids.map((row) => row.id),
    release_gate_ready: finalReadiness.release_gate.ready,
    aws_gate_ready: finalReadiness.aws_gate.ready,
    checklist_gate_ready: finalReadiness.checklist_gate.ready,
    final_candidate_status_path: finalReadiness.final_candidate_gate.status_path,
    final_candidate_ready: finalReadiness.final_candidate_gate.ready,
    external_action_plan_path: externalActionPlanPath,
    external_actions_pending: finalReadiness.external_action_gate.pending_action_ids
  },
  source_catalog: {
    path: acceptanceCatalogPath,
    item_count: acceptanceCatalog.item_count,
    priority_counts: acceptanceCatalog.priority_counts
  },
  draft_status: "draft_not_for_final_acceptance",
  pending_final_evidence: [
    "GitHub release and immutable Git tag",
    "AWS account id and deployed CloudFormation stack ids",
    "CloudFront/S3/Docusaurus/Allure published URLs",
    "Aurora DSQL Flyway apply report",
    "Final signed acceptance checklist"
  ]
};

const checklist = buildChecklist(rows);
const summary = {
  schema_version: "saphnexa-acceptance-package-summary.v1",
  generated_at: generatedAt,
  generated_by: "tools/build-acceptance-package.js",
  git_commit_sha: gitCommit,
  evidence_manifest_path: evidenceManifestPackagePath,
  trace_state_counts: effectiveCounts,
  source_catalog_path: acceptanceCatalogPath,
  source_catalog_items: acceptanceCatalog.item_count,
  source_priority_counts: acceptanceCatalog.priority_counts,
  checklist_rows: checklist.length,
  blocker_critical_open_count: defectSnapshot.blocker_critical_open_count,
  cloudformation_inventory_draft_path: cloudFormationInventoryPath,
  artifact_summary_draft_path: artifactSummaryPath,
  artifact_summary_items: artifactSummaryStats.item_count,
  artifact_summary_pending_external: artifactSummaryStats.pending_external_count,
  final_readiness_path: finalReadinessPath,
  final_readiness_ready: finalAcceptanceReady,
  final_candidate_status_path: finalReadiness.final_candidate_gate.status_path,
  final_candidate_ready: finalReadiness.final_candidate_gate.ready,
  external_action_plan_path: externalActionPlanPath,
  external_actions_pending: finalReadiness.external_action_gate.pending_action_ids.length,
  final_acceptance_ready: finalAcceptanceReady,
  note: finalAcceptanceReady
    ? "Final package summary is ready because final evidence candidate, fresh defect snapshot, and aggregate readiness gates are satisfied."
    : "Draft package for local evidence consolidation. Final acceptance still requires AWS/UAT evidence for requires_aws rows."
};

write(draftEvidenceManifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
if (finalEvidenceManifest) write(finalEvidenceManifestPackagePath, `${JSON.stringify(finalEvidenceManifest, null, 2)}\n`);
write(artifactSummaryPath, `${JSON.stringify(artifactSummary, null, 2)}\n`);
write(join(outputRoot, "acceptance_checklist.draft.csv"), renderCsv(checklist));
write(join(outputRoot, "defect_list.json"), `${JSON.stringify(defectSnapshot, null, 2)}\n`);
write(join(outputRoot, "summary.json"), `${JSON.stringify(summary, null, 2)}\n`);

console.log(`${finalAcceptanceReady ? "final acceptance package" : "acceptance package draft"} generated: ${outputRoot}`);

function parseTraceRows(body) {
  return [...body.matchAll(/^\| (AC-\d{3}) \| ([a-z_]+) \| (.+) \|$/gm)]
    .map((match) => ({ id: match[1], state: match[2], evidence: match[3].replaceAll("`", "'") }));
}

function countStates(items) {
  const counts = { local_verified: 0, requires_aws: 0, implemented_unverified: 0, scaffolded: 0, not_started: 0 };
  for (const row of items) counts[row.state] = (counts[row.state] || 0) + 1;
  return counts;
}

function buildChecklist(items) {
  const byId = new Map(items.map((item) => [item.id, item]));
  return acceptanceIds.map((id) => {
    const row = byId.get(id);
    const source = acceptanceItemById[id];
    const result = row.state === "local_verified" ? "PASS_LOCAL" : "PENDING_AWS";
    return {
      ID: id,
      領域: source.area,
      検収項目: source.item,
      "受け入れ条件 / 完了条件": source.acceptance_condition,
      定量基準: source.quantitative_criteria,
      監査証跡: source.evidence,
      確認方法: source.verification_method,
      重要度: source.priority,
      結果: result,
      証跡リンク: row.evidence,
      確認者: result === "PASS_LOCAL" ? "local-automation" : "pending-final-acceptance",
      確認日: generatedDate,
      備考: result === "PASS_LOCAL" ? "ローカル検証済み。最終検収では監査証跡URLを確認する。" : "AWS/UATまたは最終検収操作が必要。",
      state: row.state
    };
  });
}

function renderCsv(items) {
  const headers = [...sourceChecklistColumns, "state"];
  return `${headers.join(",")}\n${items.map((item) => headers.map((key) => csv(item[key])).join(",")).join("\n")}\n`;
}

function csv(value) {
  const text = String(value ?? "");
  if (!/[",\n]/.test(text)) return text;
  return `"${text.replaceAll('"', '""')}"`;
}

function write(path, body) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
}
