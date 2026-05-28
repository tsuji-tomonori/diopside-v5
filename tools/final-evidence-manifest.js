import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { currentGitCommit } from "./git-context.js";
import { readJson } from "./lib.js";

export const finalEvidenceManifestPath = "docs/acceptance/final/evidence_manifest.json";
export const finalEvidenceManifestInputPath = "docs/acceptance/final/evidence-manifest-input.uat.json";
export const finalManifestCloudFormationInventoryPath = "docs/acceptance/cloudformation/cloudformation_inventory.uat.json";

export function buildFinalEvidenceManifestFromFile(options = {}) {
  const inputPath = options.inputPath || finalEvidenceManifestInputPath;
  const inventoryPath = options.cloudFormationInventoryPath || finalManifestCloudFormationInventoryPath;
  const outputPath = options.outputPath || finalEvidenceManifestPath;
  const manifest = buildFinalEvidenceManifest({
    input: readJson(inputPath),
    inventory: readJson(inventoryPath),
    gitCommitSha: options.gitCommitSha || currentGitCommit(),
    packageJson: readJson("package.json")
  });
  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, `${JSON.stringify(manifest, null, 2)}\n`);
  return manifest;
}

export function buildFinalEvidenceManifest({ input, inventory, gitCommitSha, packageJson }) {
  validateInput(input);
  validateInventory(inventory);
  const stackArn = parseCloudFormationStackArn(inventory.stack_id);
  assert(stackArn?.accountId === input.aws_account_id, "manifest input aws_account_id must match CloudFormation inventory stack account");
  assert(stackArn?.region === inventory.aws_region, "CloudFormation inventory stack ARN region must match inventory region");
  assert(stackArn?.stackName === inventory.stack_name, "CloudFormation inventory stack ARN name must match inventory stack_name");

  return {
    system: "Saphnexa",
    environment: "uat",
    aws_region: inventory.aws_region,
    aws_account_id: input.aws_account_id,
    git_commit_sha: gitCommitSha,
    git_tag: input.git_tag,
    github_release_url: input.github_release_url,
    cdk_app_version: packageJson.version,
    cloudformation_stacks: [
      {
        stack_name: inventory.stack_name,
        stack_id: inventory.stack_id
      }
    ],
    db_migration: {
      tool: "Flyway",
      latest_version: input.db_migration.latest_version,
      checksum_status: input.db_migration.checksum_status
    },
    test_reports: input.test_reports,
    docs_site: input.docs_site,
    rag_evaluation: input.rag_evaluation,
    cost_estimate: input.cost_estimate
  };
}

function validateInput(input) {
  assert(input && typeof input === "object" && !Array.isArray(input), "manifest input must be an object");
  for (const key of [
    "aws_account_id",
    "git_tag",
    "github_release_url",
    "db_migration",
    "test_reports",
    "docs_site",
    "rag_evaluation",
    "cost_estimate"
  ]) {
    assert(Object.prototype.hasOwnProperty.call(input, key), `manifest input missing ${key}`);
  }
  assert(/^[0-9]{12}$/.test(input.aws_account_id), "manifest input aws_account_id must be a 12 digit AWS account id");
  assertFinalText(input.git_tag, "manifest input git_tag");
  assertFinalText(input.github_release_url, "manifest input github_release_url");
  assert(isReleaseUrlForTag(input.github_release_url, input.git_tag), "manifest input github_release_url must point to git_tag");
  assertFinalText(input.db_migration?.latest_version, "manifest input db_migration.latest_version");
  assert(input.db_migration?.checksum_status === "matched", "manifest input db_migration.checksum_status must be matched");
  for (const key of ["allure_latest_url", "unit_report_url", "integration_report_url", "e2e_report_url"]) {
    assertFinalText(input.test_reports?.[key], `manifest input test_reports.${key}`);
    assert(isArtifactUrl(input.test_reports?.[key]), `manifest input test_reports.${key} must be a final artifact URL`);
    assert(isAllureReportUrl(input.test_reports?.[key]), `manifest input test_reports.${key} must point to an Allure latest or run report path`);
  }
  assert(isAllureLatestUrl(input.test_reports?.allure_latest_url), "manifest input test_reports.allure_latest_url must point to the Allure latest report path");
  for (const key of ["latest_url", "version_url"]) {
    assertFinalText(input.docs_site?.[key], `manifest input docs_site.${key}`);
    assert(isArtifactUrl(input.docs_site?.[key]), `manifest input docs_site.${key} must be a final artifact URL`);
  }
  assert(isDocsLatestUrl(input.docs_site?.latest_url), "manifest input docs_site.latest_url must point to /admin/docs/latest/ or docs-site/latest/");
  assert(isDocsVersionUrl(input.docs_site?.version_url), "manifest input docs_site.version_url must point to /admin/docs/versions/v0.16/ or docs-site/releases/v0.16/");
  assertFinalText(input.rag_evaluation?.evaluation_run_id, "manifest input rag_evaluation.evaluation_run_id");
  assertFinalText(input.rag_evaluation?.report_url, "manifest input rag_evaluation.report_url");
  assert(isArtifactUrl(input.rag_evaluation?.report_url), "manifest input rag_evaluation.report_url must be a final artifact URL");
  assert(isEvaluationReportUrl(input.rag_evaluation?.report_url, input.rag_evaluation?.evaluation_run_id), "manifest input rag_evaluation.report_url must point to evaluation_run_id");
  assert(typeof input.cost_estimate?.monthly_usd === "number", "manifest input cost_estimate.monthly_usd must be a number");
  assert(input.cost_estimate.monthly_usd >= 0 && input.cost_estimate.monthly_usd <= 550, "manifest input cost_estimate.monthly_usd must be between 0 and 550");
  assertFinalText(input.cost_estimate?.assumption, "manifest input cost_estimate.assumption");
  assert(hasUsageBasis(input.cost_estimate?.assumption), "manifest input cost_estimate.assumption must mention 50 DAU and 10 questions/user/day");
}

function validateInventory(inventory) {
  assert(inventory?.schema_version === "saphnexa-cloudformation-inventory.v1", "CloudFormation inventory schema mismatch");
  assert(inventory.source === "aws-cloudformation-inventory", "CloudFormation inventory must come from AWS source");
  assert(inventory.final_acceptance_eligible === true, "CloudFormation inventory must be final acceptance eligible");
  assert(inventory.aws_capture_required === false, "CloudFormation inventory must not require more AWS capture");
  assertFinalText(inventory.stack_name, "CloudFormation inventory stack_name");
  assertFinalText(inventory.stack_id, "CloudFormation inventory stack_id");
  assertFinalText(inventory.aws_region, "CloudFormation inventory aws_region");
}

function assertFinalText(value, label) {
  assert(typeof value === "string" && value.trim().length > 0, `${label} must be populated`);
  assert(!/pending|example|draft|placeholder|not-for-acceptance/i.test(value), `${label} must be final text`);
}

function isReleaseUrlForTag(value, gitTag) {
  return parseGitHubReleaseUrl(value)?.tag === gitTag && typeof gitTag === "string" && gitTag.length > 0;
}

function parseGitHubReleaseUrl(value) {
  try {
    const url = new URL(value);
    const match = url.pathname.match(/^\/([^/]+)\/([^/]+)\/releases\/tag\/(.+)$/);
    if (url.protocol !== "https:" || url.hostname !== "github.com" || !match) return null;
    return {
      repository: `${match[1]}/${match[2]}`,
      tag: decodeURIComponent(match[3])
    };
  } catch {
    return null;
  }
}

function isArtifactUrl(value) {
  if (typeof value !== "string" || /dist\//i.test(value) || /pending|example|draft|placeholder|not-for-acceptance/i.test(value)) return false;
  if (value.startsWith("s3://")) return true;
  if (!value.startsWith("https://")) return false;
  return isPublicHttpsUrl(value);
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
  if (typeof value !== "string" || typeof evaluationRunId !== "string" || evaluationRunId.length === 0) return false;
  const encodedRunId = encodeURIComponent(evaluationRunId);
  return hasPathSuffix(value, `/admin/evaluation-reports/${encodedRunId}/`) || hasPathSuffix(value, `/reports/evaluations/${encodedRunId}/`);
}

function hasPathSuffix(value, suffix) {
  return typeof value === "string" && normalizePathSuffix(value).endsWith(suffix);
}

function normalizePathSuffix(value) {
  return value.endsWith("/") ? value : `${value}/`;
}

function hasUsageBasis(value) {
  return typeof value === "string" && value.includes("50 DAU") && value.includes("10 questions/user/day");
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

function parseCloudFormationStackArn(value) {
  const match = /^arn:aws:cloudformation:([^:]+):([0-9]{12}):stack\/([^/]+)\/.+$/.exec(value || "");
  if (!match) return null;
  return { region: match[1], accountId: match[2], stackName: match[3] };
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
