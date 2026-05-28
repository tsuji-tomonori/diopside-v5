import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { acceptanceIds, acceptanceItemById } from "./acceptance-ids.js";
import {
  assertSourceChecklistColumns,
  finalCheckedDateColumn,
  finalEvidenceColumn,
  finalResultColumn,
  finalReviewerColumn,
  sourceChecklistValue
} from "./acceptance-checklist-format.js";
import { currentGitCommit, currentGitRepository, gitTagCommit } from "./git-context.js";
import { expectedMajorOutputKeys, expectedMajorResourceTypeMinimumCounts, expectedMajorResourceTypes } from "./cloudformation-inventory.js";
import { currentJstTimestamp, listFiles, readJson, readText } from "./lib.js";

export const finalCandidateStatusPath = "dist/acceptance/final_candidate_status.json";
export const finalEvidenceManifestPath = "docs/acceptance/final/evidence_manifest.json";
export const finalChecklistPath = "docs/acceptance/final/acceptance_checklist.csv";
export const finalCloudFormationInventoryPath = "docs/acceptance/cloudformation/cloudformation_inventory.uat.json";

const candidatePaths = [
  finalEvidenceManifestPath,
  finalChecklistPath,
  finalCloudFormationInventoryPath
];

export function buildFinalEvidenceCandidateStatus(outputPath = finalCandidateStatusPath, options = {}) {
  const paths = {
    evidence_manifest: finalEvidenceManifestPath,
    acceptance_checklist: finalChecklistPath,
    cloudformation_inventory: finalCloudFormationInventoryPath,
    ...(options.candidatePaths || {})
  };
  const missing_files = Object.values(paths).filter((path) => !exists(path));
  const checks = [];
  const errors = [];

  if (missing_files.length === 0) {
    const manifest = validateManifest(paths.evidence_manifest, checks, errors, options);
    validateChecklist(paths.acceptance_checklist, checks, errors, options, manifest);
    const cloudFormationInventory = validateCloudFormationInventory(paths.cloudformation_inventory, checks, errors);
    validateManifestCloudFormationConsistency(manifest, cloudFormationInventory, checks, errors);
    validateManifestArtifactDeploymentSources(manifest, cloudFormationInventory, checks, errors);
  }

  const status = {
    schema_version: "saphnexa-final-evidence-candidate-status.v1",
    generated_at: currentJstTimestamp(),
    generated_by: "tools/check-final-evidence-candidate.js",
    ready: missing_files.length === 0 && errors.length === 0,
    status: missing_files.length > 0 ? "not_ready" : errors.length === 0 ? "ready" : "invalid",
    candidate_paths: paths,
    missing_files,
    checks,
    errors,
    note: "Final candidate files are required for acceptance completion. Missing candidate files are expected during local preflight and must not be treated as final PASS."
  };

  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, `${JSON.stringify(status, null, 2)}\n`);
  return status;
}

function validateManifest(path, checks, errors, options = {}) {
  const manifest = readJson(path);
  const packageJson = readJson("package.json");
  const resolveGitTagCommit = options.resolveGitTagCommit || gitTagCommit;
  const resolveGitRepository = options.resolveGitRepository || currentGitRepository;
  const required = [
    "system",
    "environment",
    "aws_region",
    "aws_account_id",
    "git_commit_sha",
    "git_tag",
    "github_release_url",
    "cdk_app_version",
    "cloudformation_stacks",
    "db_migration",
    "test_reports",
    "docs_site",
    "rag_evaluation",
    "cost_estimate"
  ];
  for (const key of required) requireField(manifest, key, `manifest.${key}`, errors);

  validateNoForbiddenManifestMarkers(manifest, checks, errors);
  check(manifest.system === "Saphnexa", "manifest.system", checks, errors, "must be Saphnexa");
  check(manifest.environment === "uat", "manifest.environment", checks, errors, "must be uat");
  check(manifest.aws_region === "ap-northeast-1", "manifest.aws_region", checks, errors, "must be ap-northeast-1");
  check(isRealAwsAccountId(manifest.aws_account_id), "manifest.aws_account_id", checks, errors, "must be a real 12 digit AWS account id");
  check(/^[a-f0-9]{40}$/.test(manifest.git_commit_sha || "") && !/^0{40}$/.test(manifest.git_commit_sha || ""), "manifest.git_commit_sha", checks, errors, "must be a non-placeholder commit SHA");
  check(manifest.git_commit_sha === currentGitCommit(), "manifest.git_commit_sha_current_ref", checks, errors, "must match current Git ref");
  check(isFinalText(manifest.git_tag), "manifest.git_tag", checks, errors, "must be a final immutable Git tag");
  const tagCommit = resolveGitTagCommit(manifest.git_tag);
  check(Boolean(tagCommit), "manifest.git_tag_ref", checks, errors, "must exist as a Git tag ref");
  check(tagCommit === manifest.git_commit_sha, "manifest.git_tag_commit", checks, errors, "must point to manifest.git_commit_sha");
  check(isUrl(manifest.github_release_url), "manifest.github_release_url", checks, errors, "must be an https GitHub release URL");
  check(isReleaseUrlForTag(manifest.github_release_url, manifest.git_tag), "manifest.github_release_url_git_tag", checks, errors, "must point to the same release tag as manifest.git_tag");
  const releaseRef = parseGitHubReleaseUrl(manifest.github_release_url);
  const currentRepository = resolveGitRepository();
  check(Boolean(currentRepository), "manifest.github_release_url_current_repo_available", checks, errors, "current GitHub repository must be resolvable from remote.origin.url");
  check(releaseRef?.repository === currentRepository, "manifest.github_release_url_repository", checks, errors, "must point to the current GitHub repository release");
  check(isFinalText(manifest.cdk_app_version), "manifest.cdk_app_version", checks, errors, "must include final CDK app version");
  check(manifest.cdk_app_version === packageJson.version, "manifest.cdk_app_version_package_version", checks, errors, "must match package.json version");
  check(Array.isArray(manifest.cloudformation_stacks) && manifest.cloudformation_stacks.length > 0, "manifest.cloudformation_stacks", checks, errors, "must include deployed stacks");
  for (const stack of manifest.cloudformation_stacks || []) {
    const stackArn = parseCloudFormationStackArn(stack.stack_id);
    check(isFinalText(stack.stack_name), `manifest.cloudformation_stacks.${stack.stack_name || "unknown"}.stack_name`, checks, errors, "must include stack name");
    check(/^arn:aws:cloudformation:ap-northeast-1:[0-9]{12}:stack\//.test(stack.stack_id || ""), `manifest.cloudformation_stacks.${stack.stack_name || "unknown"}.stack_id`, checks, errors, "must include CloudFormation stack ARN");
    check(stackArn?.region === manifest.aws_region, `manifest.cloudformation_stacks.${stack.stack_name || "unknown"}.stack_region`, checks, errors, "stack ARN region must match manifest.aws_region");
    check(stackArn?.accountId === manifest.aws_account_id, `manifest.cloudformation_stacks.${stack.stack_name || "unknown"}.stack_account`, checks, errors, "stack ARN account must match manifest.aws_account_id");
    check(stackArn?.stackName === stack.stack_name, `manifest.cloudformation_stacks.${stack.stack_name || "unknown"}.stack_name_arn`, checks, errors, "stack_name must match stack ARN name");
  }

  for (const key of ["allure_latest_url", "unit_report_url", "integration_report_url", "e2e_report_url"]) {
    check(isArtifactUrl(manifest.test_reports?.[key]), `manifest.test_reports.${key}`, checks, errors, "must be a final http(s) or s3 URL");
    check(isAllureReportUrl(manifest.test_reports?.[key]), `manifest.test_reports.${key}_allure_path`, checks, errors, "must point to an Allure latest or run report path");
  }
  check(isAllureLatestUrl(manifest.test_reports?.allure_latest_url), "manifest.test_reports.allure_latest_url_latest_path", checks, errors, "must point to the Allure latest report path");
  for (const key of ["latest_url", "version_url"]) {
    check(isArtifactUrl(manifest.docs_site?.[key]), `manifest.docs_site.${key}`, checks, errors, "must be a final http(s) or s3 URL");
  }
  check(isDocsLatestUrl(manifest.docs_site?.latest_url), "manifest.docs_site.latest_url_admin_docs_path", checks, errors, "must point to /admin/docs/latest/ or docs-site/latest/");
  check(isDocsVersionUrl(manifest.docs_site?.version_url), "manifest.docs_site.version_url_admin_docs_path", checks, errors, "must point to /admin/docs/versions/v0.16/ or docs-site/releases/v0.16/");
  check(isFinalText(manifest.rag_evaluation?.evaluation_run_id), "manifest.rag_evaluation.evaluation_run_id", checks, errors, "must include final evaluation run id");
  check(isArtifactUrl(manifest.rag_evaluation?.report_url), "manifest.rag_evaluation.report_url", checks, errors, "must be a final report URL");
  check(isEvaluationReportUrl(manifest.rag_evaluation?.report_url, manifest.rag_evaluation?.evaluation_run_id), "manifest.rag_evaluation.report_url_evaluation_run", checks, errors, "must point to the evaluation report path for evaluation_run_id");
  check(manifest.db_migration?.tool === "Flyway", "manifest.db_migration.tool", checks, errors, "must be Flyway");
  check(isFinalText(manifest.db_migration?.latest_version), "manifest.db_migration.latest_version", checks, errors, "must include final DB migration version");
  check(manifest.db_migration?.latest_version === latestFlywayMigrationFile(), "manifest.db_migration.latest_version_latest_file", checks, errors, "must match latest Flyway migration file");
  check(manifest.db_migration?.checksum_status === "matched", "manifest.db_migration.checksum_status", checks, errors, "must be matched");
  check(isAcceptedMonthlyUsd(manifest.cost_estimate?.monthly_usd), "manifest.cost_estimate.monthly_usd", checks, errors, "must be a finite number between 0 and 550");
  check(isFinalText(manifest.cost_estimate?.assumption), "manifest.cost_estimate.assumption", checks, errors, "must include final cost assumption");
  check(hasUsageBasis(manifest.cost_estimate?.assumption), "manifest.cost_estimate.assumption_usage_basis", checks, errors, "must mention 50 DAU and 10 questions/user/day");
  return manifest;
}

function validateChecklist(path, checks, errors, options = {}, manifest) {
  const rows = parseCsv(readText(path));
  const currentDate = options.currentDate || todayIsoDate();
  checkSourceColumns(rows.headers, checks, errors);
  check(rows.length === acceptanceIds.length, "checklist.row_count", checks, errors, `must contain ${acceptanceIds.length} rows`);
  validateChecklistRowIdentity(rows, checks, errors);
  for (const id of acceptanceIds) {
    const row = rows.find((item) => item.ID === id);
    check(Boolean(row), `checklist.${id}`, checks, errors, "must exist");
    if (!row) continue;
    const source = acceptanceItemById[id];
    check(row["領域"] === source.area, `checklist.${id}.領域`, checks, errors, "must match source checklist area");
    check(row["重要度"] === source.priority, `checklist.${id}.重要度`, checks, errors, "must match source checklist priority");
    check(row["検収項目"] === source.item, `checklist.${id}.検収項目`, checks, errors, "must match source checklist item");
    check(row["受け入れ条件 / 完了条件"] === source.acceptance_condition, `checklist.${id}.受け入れ条件`, checks, errors, "must match source checklist condition");
    for (const key of [finalResultColumn, finalEvidenceColumn, finalReviewerColumn, finalCheckedDateColumn]) {
      check(isFinalText(sourceChecklistValue(row, key)), `checklist.${id}.${key}`, checks, errors, "must be populated");
    }
    check(sourceChecklistValue(row, finalResultColumn) === "PASS", `checklist.${id}.${finalResultColumn}`, checks, errors, "must be PASS for final acceptance");
    const evidenceUrl = sourceChecklistValue(row, finalEvidenceColumn);
    check(isArtifactUrl(evidenceUrl), `checklist.${id}.${finalEvidenceColumn}_url`, checks, errors, "must be a final http(s) or s3 evidence URL");
    check(isKnownChecklistEvidenceUrl(evidenceUrl, manifest), `checklist.${id}.${finalEvidenceColumn}_known_source`, checks, errors, "must point to the current GitHub repository or manifest artifact location");
    check(isFinalReviewer(sourceChecklistValue(row, finalReviewerColumn)), `checklist.${id}.${finalReviewerColumn}_reviewer`, checks, errors, "must name a final reviewer");
    check(isIsoDate(sourceChecklistValue(row, finalCheckedDateColumn)), `checklist.${id}.${finalCheckedDateColumn}_date`, checks, errors, "must be a YYYY-MM-DD calendar date");
    check(isIsoDateOnOrBefore(sourceChecklistValue(row, finalCheckedDateColumn), currentDate), `checklist.${id}.${finalCheckedDateColumn}_not_future`, checks, errors, "must not be a future date");
    check(!/PENDING|PASS_LOCAL|requires_aws/i.test(Object.values(row).join(" ")), `checklist.${id}.no_draft_status`, checks, errors, "must not contain draft status markers");
    check(!hasForbiddenFinalMarker(Object.values(row).join(" ")), `checklist.${id}.no_forbidden_markers`, checks, errors, "must not contain draft, placeholder, example, pending, or not-for-acceptance markers");
  }
}

function validateChecklistRowIdentity(rows, checks, errors) {
  const rowIds = rows.map((row) => row.ID);
  check(new Set(rowIds).size === rowIds.length, "checklist.unique_ids", checks, errors, "must not contain duplicate IDs");
  check(JSON.stringify(rowIds) === JSON.stringify(acceptanceIds), "checklist.source_order", checks, errors, "must preserve source catalog ID order");
}

function validateNoForbiddenManifestMarkers(manifest, checks, errors) {
  for (const [path, value] of objectStringEntries(manifest)) {
    check(!hasForbiddenFinalMarker(value), `manifest.no_forbidden_markers.${path}`, checks, errors, "must not contain draft, placeholder, example, pending, or not-for-acceptance markers");
  }
}

function objectStringEntries(value, prefix = "") {
  if (typeof value === "string") return [[prefix || "root", value]];
  if (!value || typeof value !== "object") return [];
  if (Array.isArray(value)) return value.flatMap((item, index) => objectStringEntries(item, `${prefix}[${index}]`));
  return Object.entries(value).flatMap(([key, item]) => objectStringEntries(item, prefix ? `${prefix}.${key}` : key));
}

function checkSourceColumns(headers, checks, errors) {
  try {
    assertSourceChecklistColumns(headers, (condition, message) => {
      if (!condition) throw new Error(message);
    });
    checks.push({ label: "checklist.source_columns", result: "pass", message: "must include source checklist columns" });
  } catch (error) {
    checks.push({ label: "checklist.source_columns", result: "fail", message: "must include source checklist columns" });
    errors.push(`checklist.source_columns: ${error.message}`);
  }
}

function validateCloudFormationInventory(path, checks, errors) {
  const inventory = readJson(path);
  check(inventory.schema_version === "saphnexa-cloudformation-inventory.v1", "cloudformation.schema_version", checks, errors, "must match schema");
  check(inventory.source === "aws-cloudformation-inventory", "cloudformation.source", checks, errors, "must come from AWS CloudFormation inventory");
  check(inventory.final_acceptance_eligible === true, "cloudformation.final_acceptance_eligible", checks, errors, "must be final acceptance eligible");
  check(inventory.aws_capture_required === false, "cloudformation.aws_capture_required", checks, errors, "must not require more AWS capture");
  check(/^arn:aws:cloudformation:ap-northeast-1:[0-9]{12}:stack\//.test(inventory.stack_id || ""), "cloudformation.stack_id", checks, errors, "must include stack ARN");
  check(isCompleteCloudFormationStackStatus(inventory.stack_status), "cloudformation.stack_status", checks, errors, "must be a complete CloudFormation stack status");
  validateCloudFormationCaptureEvidence(inventory, checks, errors);
  check(Array.isArray(inventory.stack_outputs) && inventory.stack_outputs.length > 0, "cloudformation.stack_outputs", checks, errors, "must include stack outputs");
  check(Array.isArray(inventory.stack_resources) && inventory.stack_resources.length > 0, "cloudformation.stack_resources", checks, errors, "must include resources");
  for (const output of inventory.stack_outputs || []) {
    check(isFinalText(output.OutputKey), `cloudformation.output.${output.OutputKey || "unknown"}.OutputKey`, checks, errors, "must include output key");
    check(isFinalText(output.OutputValue), `cloudformation.output.${output.OutputKey || "unknown"}.OutputValue`, checks, errors, "must include output value");
  }
  const outputKeys = new Set((inventory.stack_outputs || []).map((output) => normalizeOutputKey(output.OutputKey)));
  for (const outputKey of expectedMajorOutputKeys) {
    check(outputKeys.has(normalizeOutputKey(outputKey)), `cloudformation.major_output_key.${outputKey}`, checks, errors, "must include expected major output key");
  }
  for (const resource of inventory.stack_resources || []) {
    const label = resource.LogicalResourceId || resource.ResourceType || "unknown";
    check(isFinalText(resource.LogicalResourceId), `cloudformation.resource.${label}.LogicalResourceId`, checks, errors, "must include logical resource id");
    check(isFinalText(resource.PhysicalResourceId), `cloudformation.resource.${label}.PhysicalResourceId`, checks, errors, "must include physical resource id");
    check(/^AWS::/.test(resource.ResourceType || ""), `cloudformation.resource.${label}.ResourceType`, checks, errors, "must include AWS resource type");
    check(isCompleteCloudFormationResourceStatus(resource.ResourceStatus), `cloudformation.resource.${label}.ResourceStatus`, checks, errors, "must include a complete resource status");
  }
  const resourceTypeCounts = countBy((inventory.stack_resources || []).map((resource) => resource.ResourceType).filter(Boolean));
  const resourceTypes = new Set(resourceTypeCounts.keys());
  for (const resourceType of expectedMajorResourceTypes) {
    check(resourceTypes.has(resourceType), `cloudformation.major_resource_type.${resourceType}`, checks, errors, "must include expected major resource type");
    check((resourceTypeCounts.get(resourceType) || 0) >= expectedMajorResourceTypeMinimumCounts[resourceType], `cloudformation.major_resource_type_count.${resourceType}`, checks, errors, `must include at least ${expectedMajorResourceTypeMinimumCounts[resourceType]} resources of this type`);
  }
  return inventory;
}

function validateCloudFormationCaptureEvidence(inventory, checks, errors) {
  const evidence = inventory.capture_evidence;
  const hasEvidence = Boolean(evidence) && typeof evidence === "object" && !Array.isArray(evidence);
  check(hasEvidence, "cloudformation.capture_evidence", checks, errors, "must include CloudFormation capture evidence metadata");
  if (!hasEvidence) return;
  check(isIsoDateTime(evidence.captured_at), "cloudformation.capture_evidence.captured_at", checks, errors, "must be an ISO timestamp");
  check(
    isCloudFormationCaptureCommand(evidence.describe_stacks_command, "describe-stacks", inventory.stack_name),
    "cloudformation.capture_evidence.describe_stacks_command",
    checks,
    errors,
    "must record describe-stacks command for this stack and region"
  );
  check(
    isCloudFormationCaptureCommand(evidence.list_stack_resources_command, "list-stack-resources", inventory.stack_name),
    "cloudformation.capture_evidence.list_stack_resources_command",
    checks,
    errors,
    "must record list-stack-resources command for this stack and region"
  );
}

function validateManifestCloudFormationConsistency(manifest, inventory, checks, errors) {
  const manifestStacks = Array.isArray(manifest.cloudformation_stacks) ? manifest.cloudformation_stacks : [];
  const inventoryStackArn = parseCloudFormationStackArn(inventory.stack_id);
  const manifestStack = manifestStacks.find((stack) => stack.stack_id === inventory.stack_id);

  check(manifest.system === inventory.system, "final_evidence.system_consistency", checks, errors, "manifest and CloudFormation inventory must use the same system");
  check(manifest.environment === inventory.environment, "final_evidence.environment_consistency", checks, errors, "manifest and CloudFormation inventory must use the same environment");
  check(manifest.aws_region === inventory.aws_region, "final_evidence.aws_region_consistency", checks, errors, "manifest and CloudFormation inventory must use the same AWS region");
  check(inventoryStackArn?.accountId === manifest.aws_account_id, "final_evidence.aws_account_consistency", checks, errors, "CloudFormation inventory stack ARN account must match manifest.aws_account_id");
  check(inventoryStackArn?.region === manifest.aws_region, "final_evidence.stack_region_consistency", checks, errors, "CloudFormation inventory stack ARN region must match manifest.aws_region");
  check(Boolean(manifestStack), "final_evidence.stack_id_consistency", checks, errors, "CloudFormation inventory stack_id must be listed in manifest.cloudformation_stacks");
  check(manifestStack?.stack_name === inventory.stack_name, "final_evidence.stack_name_consistency", checks, errors, "CloudFormation inventory stack_name must match the manifest stack name for the same stack_id");
}

function validateManifestArtifactDeploymentSources(manifest, inventory, checks, errors) {
  const deploymentSources = artifactDeploymentSources(inventory);
  check(deploymentSources.size > 0, "final_evidence.artifact_deployment_sources", checks, errors, "CloudFormation inventory must include artifact deployment outputs");
  for (const [label, value] of manifestArtifactEntries(manifest)) {
    check(
      artifactUrlMatchesDeploymentSource(value, deploymentSources),
      `final_evidence.artifact_deployment_source.${label}`,
      checks,
      errors,
      "artifact URL must point to the CloudFormation distribution or admin artifacts bucket"
    );
  }
}

function requireField(object, key, label, errors) {
  if (!Object.prototype.hasOwnProperty.call(object, key)) errors.push(`${label}: required`);
}

function check(condition, label, checks, errors, message) {
  checks.push({ label, result: condition ? "pass" : "fail", message });
  if (!condition) errors.push(`${label}: ${message}`);
}

function exists(path) {
  try {
    readText(path);
    return true;
  } catch {
    return false;
  }
}

function countBy(values) {
  const counts = new Map();
  for (const value of values) counts.set(value, (counts.get(value) || 0) + 1);
  return counts;
}

function isFinalText(value) {
  return typeof value === "string" && value.length > 0 && !hasForbiddenFinalMarker(value);
}

function isRealAwsAccountId(value) {
  return /^[0-9]{12}$/.test(value || "") && !/^([0-9])\1{11}$/.test(value || "") && !commonPlaceholderAwsAccountIds().has(value);
}

function commonPlaceholderAwsAccountIds() {
  return new Set([["1234", "5678", "9012"].join("")]);
}

function isUrl(value) {
  return typeof value === "string" && /^https:\/\/github\.com\//.test(value) && !hasForbiddenFinalMarker(value);
}

function isReleaseUrlForTag(value, gitTag) {
  return parseGitHubReleaseUrl(value)?.tag === gitTag && isFinalText(gitTag);
}

function isArtifactUrl(value) {
  if (typeof value !== "string" || hasForbiddenFinalMarker(value) || /dist\//i.test(value)) return false;
  if (value.startsWith("s3://")) return true;
  if (!value.startsWith("https://")) return false;
  return isPublicHttpsUrl(value);
}

function hasForbiddenFinalMarker(value) {
  return /pending|example|draft|placeholder|not-for-acceptance/i.test(value || "");
}

function isKnownChecklistEvidenceUrl(value, manifest) {
  if (!isArtifactUrl(value)) return false;
  const releaseRepository = parseGitHubReleaseUrl(manifest?.github_release_url)?.repository;
  if (releaseRepository && isGitHubRepositoryEvidenceUrl(value, releaseRepository)) return true;
  return manifestArtifactLocations(manifest).some((artifactUrl) => sharesArtifactLocation(value, artifactUrl));
}

function manifestArtifactLocations(manifest) {
  return manifestArtifactEntries(manifest).map(([, value]) => value).filter(isArtifactUrl);
}

function manifestArtifactEntries(manifest) {
  return [
    ["test_reports.allure_latest_url", manifest?.test_reports?.allure_latest_url],
    ["test_reports.unit_report_url", manifest?.test_reports?.unit_report_url],
    ["test_reports.integration_report_url", manifest?.test_reports?.integration_report_url],
    ["test_reports.e2e_report_url", manifest?.test_reports?.e2e_report_url],
    ["docs_site.latest_url", manifest?.docs_site?.latest_url],
    ["docs_site.version_url", manifest?.docs_site?.version_url],
    ["rag_evaluation.report_url", manifest?.rag_evaluation?.report_url]
  ].filter(([, value]) => isArtifactUrl(value));
}

function isGitHubRepositoryEvidenceUrl(value, repository) {
  try {
    const url = new URL(value);
    return url.hostname === "github.com" && (url.pathname === `/${repository}` || url.pathname.startsWith(`/${repository}/`));
  } catch {
    return false;
  }
}

function sharesArtifactLocation(value, artifactUrl) {
  const left = artifactLocation(value);
  const right = artifactLocation(artifactUrl);
  return Boolean(left && right && left === right);
}

function artifactLocation(value) {
  const s3 = parseS3Url(value);
  if (s3) return `s3://${s3.bucket}`;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:") return null;
    return `https://${url.hostname.toLowerCase()}`;
  } catch {
    return null;
  }
}

function parseS3Url(value) {
  const match = /^s3:\/\/([^/]+)(?:\/.*)?$/.exec(value || "");
  if (!match) return null;
  return { bucket: match[1] };
}

function artifactDeploymentSources(inventory) {
  const sources = new Set();
  const distributionDomain = stackOutputValue(inventory, "DistributionDomainName");
  if (isFinalText(distributionDomain)) sources.add(`https://${distributionDomain.toLowerCase()}`);
  const artifactsBucketArn = stackOutputValue(inventory, "AdminArtifactsBucketArn");
  const artifactsBucket = parseS3BucketArn(artifactsBucketArn);
  if (artifactsBucket) sources.add(`s3://${artifactsBucket}`);
  return sources;
}

function artifactUrlMatchesDeploymentSource(value, deploymentSources) {
  const location = artifactLocation(value);
  return Boolean(location && deploymentSources.has(location));
}

function stackOutputValue(inventory, outputKey) {
  const expected = normalizeOutputKey(outputKey);
  return (inventory?.stack_outputs || []).find((output) => normalizeOutputKey(output.OutputKey) === expected)?.OutputValue;
}

function parseS3BucketArn(value) {
  const match = /^arn:aws:s3:::([^/]+)$/.exec(value || "");
  return match?.[1] || null;
}

function hasPathSuffix(value, suffix) {
  return typeof value === "string" && normalizePathSuffix(value).endsWith(suffix);
}

function isAllureLatestUrl(value) {
  return hasPathSuffix(value, "/test-reports/allure/latest/");
}

function isAllureReportUrl(value) {
  if (typeof value !== "string") return false;
  const normalized = normalizePathSuffix(value);
  return isAllureLatestUrl(normalized) || /\/test-reports\/allure\/runs\/[^/]+\/$/.test(normalized);
}

function isDocsLatestUrl(value) {
  return hasPathSuffix(value, "/admin/docs/latest/") || hasPathSuffix(value, "/docs-site/latest/");
}

function isDocsVersionUrl(value) {
  return hasPathSuffix(value, "/admin/docs/versions/v0.16/") || hasPathSuffix(value, "/docs-site/releases/v0.16/");
}

function isEvaluationReportUrl(value, evaluationRunId) {
  if (typeof value !== "string" || !isFinalText(evaluationRunId)) return false;
  const encodedRunId = encodeURIComponent(evaluationRunId);
  return hasPathSuffix(value, `/admin/evaluation-reports/${encodedRunId}/`) || hasPathSuffix(value, `/reports/evaluations/${encodedRunId}/`);
}

function normalizePathSuffix(value) {
  return value.endsWith("/") ? value : `${value}/`;
}

function isAcceptedMonthlyUsd(value) {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 550;
}

function hasUsageBasis(value) {
  return typeof value === "string" && value.includes("50 DAU") && value.includes("10 questions/user/day");
}

function isFinalReviewer(value) {
  return isFinalText(value?.trim?.()) && !/\s{2,}/.test(value);
}

function isIsoDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function isIsoDateTime(value) {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})$/.exec(value || "");
  if (typeof value !== "string" || !match || !isIsoDate(match[1])) return false;
  const [, , hour, minute, second] = match;
  if (Number(hour) > 23 || Number(minute) > 59 || Number(second) > 59) return false;
  return !Number.isNaN(new Date(value).getTime());
}

function isIsoDateOnOrBefore(value, currentDate) {
  return isIsoDate(value) && isIsoDate(currentDate) && value <= currentDate;
}

function isCloudFormationCaptureCommand(value, action, stackName) {
  return (
    isFinalText(value) &&
    value.includes(`aws cloudformation ${action}`) &&
    value.includes("--stack-name") &&
    value.includes(stackName) &&
    value.includes("--region") &&
    value.includes("ap-northeast-1")
  );
}

function isCompleteCloudFormationStackStatus(value) {
  return [
    "CREATE_COMPLETE",
    "UPDATE_COMPLETE",
    "UPDATE_ROLLBACK_COMPLETE",
    "IMPORT_COMPLETE",
    "IMPORT_ROLLBACK_COMPLETE"
  ].includes(value);
}

function isCompleteCloudFormationResourceStatus(value) {
  return [
    "CREATE_COMPLETE",
    "UPDATE_COMPLETE",
    "UPDATE_ROLLBACK_COMPLETE",
    "IMPORT_COMPLETE",
    "IMPORT_ROLLBACK_COMPLETE"
  ].includes(value);
}

function latestFlywayMigrationFile() {
  const migrationFiles = listFiles(["packages/db-migrations/migrations"], (path) => /\/V\d+__.+\.sql$/.test(path));
  return migrationFiles
    .map((path) => path.split("/").at(-1))
    .sort((left, right) => migrationVersionNumber(right) - migrationVersionNumber(left) || right.localeCompare(left))
    .at(0);
}

function migrationVersionNumber(fileName) {
  return Number(fileName.match(/^V(\d+)__/)?.[1] || 0);
}

function todayIsoDate() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function parseGitHubReleaseUrl(value) {
  if (!isUrl(value)) return null;
  try {
    const url = new URL(value);
    const match = url.pathname.match(/^\/([^/]+)\/([^/]+)\/releases\/tag\/(.+)$/);
    if (url.hostname !== "github.com" || !match) return null;
    return {
      repository: `${match[1]}/${match[2]}`,
      tag: decodeURIComponent(match[3])
    };
  } catch {
    return null;
  }
}

function parseCloudFormationStackArn(value) {
  const match = /^arn:aws:cloudformation:([^:]+):([0-9]{12}):stack\/([^/]+)\/.+$/.exec(value || "");
  if (!match) return null;
  return { region: match[1], accountId: match[2], stackName: match[3] };
}

function isPublicHttpsUrl(value) {
  try {
    const { hostname } = new URL(value);
    const normalized = hostname.toLowerCase();
    if (
      normalized === "localhost" ||
      normalized.endsWith(".localhost") ||
      normalized.endsWith(".local") ||
      normalized.endsWith(".internal") ||
      normalized.endsWith(".test")
    ) {
      return false;
    }
    if (isPrivateIpv4(normalized) || normalized === "::1" || normalized === "[::1]") return false;
    return normalized.includes(".");
  } catch {
    return false;
  }
}

function isPrivateIpv4(hostname) {
  const parts = hostname.split(".");
  if (parts.length !== 4 || parts.some((part) => !/^\d+$/.test(part))) return false;
  const [a, b, c, d] = parts.map(Number);
  if ([a, b, c, d].some((part) => part < 0 || part > 255)) return false;
  return a === 10 || a === 127 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || (a === 169 && b === 254);
}

function normalizeOutputKey(value) {
  return String(value || "").replaceAll(/[^a-z0-9]/gi, "").toLowerCase();
}

function parseCsv(body) {
  const lines = body.trim().split(/\r?\n/);
  const headers = splitCsvLine(lines[0]).map((header) => header.replace(/^\uFEFF/, ""));
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
