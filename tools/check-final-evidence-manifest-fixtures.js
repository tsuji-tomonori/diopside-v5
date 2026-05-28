import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { sourceChecklistColumns } from "./acceptance-checklist-format.js";
import { acceptanceIds, acceptanceItemById } from "./acceptance-ids.js";
import { expectedMajorOutputKeys, expectedMajorResourceTypeMinimumCounts, expectedMajorResourceTypes } from "./cloudformation-inventory.js";
import { buildFinalEvidenceCandidateStatus } from "./final-evidence-candidate.js";
import { buildFinalEvidenceManifestFromFile, buildFinalEvidenceManifest } from "./final-evidence-manifest.js";
import { currentGitCommit } from "./git-context.js";
import { assert, readJson } from "./lib.js";

const root = mkdtempSync(join(tmpdir(), "saphnexa-final-manifest-"));

try {
  const inputPath = join(root, "evidence-manifest-input.uat.json");
  const inventoryPath = join(root, "cloudformation_inventory.uat.json");
  const manifestPath = join(root, "evidence_manifest.json");
  const checklistPath = join(root, "acceptance_checklist.csv");
  writeFileSync(inputPath, `${JSON.stringify(manifestInputFixture(), null, 2)}\n`);
  writeFileSync(inventoryPath, `${JSON.stringify(cloudFormationInventoryFixture(), null, 2)}\n`);
  writeFileSync(checklistPath, renderChecklistFixture());

  const manifest = buildFinalEvidenceManifestFromFile({ inputPath, cloudFormationInventoryPath: inventoryPath, outputPath: manifestPath });
  const written = readJson(manifestPath);
  assert(JSON.stringify(manifest) === JSON.stringify(written), "written manifest must match returned manifest");
  assert(written.system === "Saphnexa", "manifest system mismatch");
  assert(written.environment === "uat", "manifest environment mismatch");
  assert(written.aws_region === "ap-northeast-1", "manifest region mismatch");
  assert(written.aws_account_id === readyAwsAccountId(), "manifest AWS account mismatch");
  assert(written.git_commit_sha === currentGitCommit(), "manifest git commit must be current ref");
  assert(written.cdk_app_version === readJson("package.json").version, "manifest cdk app version must match package version");
  assert(written.cloudformation_stacks[0].stack_id === cloudFormationInventoryFixture().stack_id, "manifest stack id must come from inventory");

  const status = buildFinalEvidenceCandidateStatus(join(root, "final-candidate-status.json"), {
    candidatePaths: {
      evidence_manifest: manifestPath,
      acceptance_checklist: checklistPath,
      cloudformation_inventory: inventoryPath
    },
    resolveGitTagCommit: (tagName) => (tagName === "v0.16.0-acceptance.1" ? currentGitCommit() : null),
    resolveGitRepository: () => "tsuji-tomonori/saphnexa",
    currentDate: "2026-05-27"
  });
  assert(status.ready === true, `manifest builder fixture must produce final-candidate-ready files: ${status.errors.join("; ")}`);
  assert(status.errors.length === 0, "manifest builder fixture must not produce final candidate errors");

  assertThrows(
    () =>
      buildFinalEvidenceManifest({
        input: { ...manifestInputFixture(), github_release_url: "" },
        inventory: cloudFormationInventoryFixture(),
        gitCommitSha: currentGitCommit(),
        packageJson: readJson("package.json")
      }),
    "manifest input github_release_url must be populated"
  );
  assertThrows(
    () =>
      buildFinalEvidenceManifest({
        input: { ...manifestInputFixture(), aws_account_id: ["2109", "8765", "4322"].join("") },
        inventory: cloudFormationInventoryFixture(),
        gitCommitSha: currentGitCommit(),
        packageJson: readJson("package.json")
      }),
    "aws_account_id must match"
  );
  assertThrows(
    () =>
      buildFinalEvidenceManifest({
        input: { ...manifestInputFixture(), github_release_url: "https://github.com/tsuji-tomonori/saphnexa/releases/tag/v0.16.0-acceptance.2" },
        inventory: cloudFormationInventoryFixture(),
        gitCommitSha: currentGitCommit(),
        packageJson: readJson("package.json")
      }),
    "github_release_url must point to git_tag"
  );
  assertThrows(
    () =>
      buildFinalEvidenceManifest({
        input: {
          ...manifestInputFixture(),
          test_reports: { ...manifestInputFixture().test_reports, allure_latest_url: "s3://saphnexa-uat-admin-artifacts/test-reports/allure/runs/unit-20260527/" }
        },
        inventory: cloudFormationInventoryFixture(),
        gitCommitSha: currentGitCommit(),
        packageJson: readJson("package.json")
      }),
    "allure_latest_url must point to the Allure latest report path"
  );
  assertThrows(
    () =>
      buildFinalEvidenceManifest({
        input: {
          ...manifestInputFixture(),
          docs_site: { ...manifestInputFixture().docs_site, latest_url: "s3://saphnexa-uat-admin-artifacts/docs/latest/" }
        },
        inventory: cloudFormationInventoryFixture(),
        gitCommitSha: currentGitCommit(),
        packageJson: readJson("package.json")
      }),
    "docs_site.latest_url must point to"
  );
  assertThrows(
    () =>
      buildFinalEvidenceManifest({
        input: {
          ...manifestInputFixture(),
          rag_evaluation: {
            ...manifestInputFixture().rag_evaluation,
            report_url: "s3://saphnexa-uat-admin-artifacts/reports/evaluations/eval-20260527-other/"
          }
        },
        inventory: cloudFormationInventoryFixture(),
        gitCommitSha: currentGitCommit(),
        packageJson: readJson("package.json")
      }),
    "rag_evaluation.report_url must point to evaluation_run_id"
  );
  assertThrows(
    () =>
      buildFinalEvidenceManifest({
        input: {
          ...manifestInputFixture(),
          cost_estimate: { ...manifestInputFixture().cost_estimate, assumption: "UAT monthly estimate." }
        },
        inventory: cloudFormationInventoryFixture(),
        gitCommitSha: currentGitCommit(),
        packageJson: readJson("package.json")
      }),
    "cost_estimate.assumption must mention 50 DAU and 10 questions/user/day"
  );

  console.log("final evidence manifest fixture check passed");
} finally {
  rmSync(root, { recursive: true, force: true });
}

function manifestInputFixture() {
  return {
    aws_account_id: readyAwsAccountId(),
    git_tag: "v0.16.0-acceptance.1",
    github_release_url: "https://github.com/tsuji-tomonori/saphnexa/releases/tag/v0.16.0-acceptance.1",
    db_migration: {
      latest_version: "V001__initial_saphnexa_schema.sql",
      checksum_status: "matched"
    },
    test_reports: {
      allure_latest_url: "s3://saphnexa-uat-admin-artifacts/test-reports/allure/latest/",
      unit_report_url: "s3://saphnexa-uat-admin-artifacts/test-reports/allure/runs/unit-20260527/",
      integration_report_url: "s3://saphnexa-uat-admin-artifacts/test-reports/allure/runs/integration-20260527/",
      e2e_report_url: "s3://saphnexa-uat-admin-artifacts/test-reports/allure/runs/e2e-20260527/"
    },
    docs_site: {
      latest_url: "s3://saphnexa-uat-admin-artifacts/docs-site/latest/",
      version_url: "s3://saphnexa-uat-admin-artifacts/docs-site/releases/v0.16/"
    },
    rag_evaluation: {
      evaluation_run_id: "eval-20260527-uat-final",
      report_url: "s3://saphnexa-uat-admin-artifacts/reports/evaluations/eval-20260527-uat-final/"
    },
    cost_estimate: {
      monthly_usd: 420,
      assumption: "UAT estimate for 50 DAU and 10 questions/user/day."
    }
  };
}

function cloudFormationInventoryFixture() {
  const accountId = readyAwsAccountId();
  const stackId = `arn:aws:cloudformation:ap-northeast-1:${accountId}:stack/saphnexa-uat-app/abc12345`;
  return {
    schema_version: "saphnexa-cloudformation-inventory.v1",
    system: "Saphnexa",
    environment: "uat",
    aws_region: "ap-northeast-1",
    stack_name: "saphnexa-uat-app",
    stack_id: stackId,
    stack_status: "UPDATE_COMPLETE",
    source: "aws-cloudformation-inventory",
    final_acceptance_eligible: true,
    aws_capture_required: false,
    capture_evidence: {
      captured_at: "2026-05-27T12:00:00+09:00",
      describe_stacks_command: "aws cloudformation describe-stacks --stack-name saphnexa-uat-app --region ap-northeast-1 --output json",
      list_stack_resources_command: "aws cloudformation list-stack-resources --stack-name saphnexa-uat-app --region ap-northeast-1 --output json"
    },
    stack_outputs: expectedMajorOutputKeys.map((outputKey, index) => ({
      OutputKey: outputKey,
      OutputValue: outputValueFor(outputKey, index)
    })),
    stack_resources: expectedMajorResources()
  };
}

function expectedMajorResources() {
  return expectedMajorResourceTypes.flatMap((resourceType) =>
    Array.from({ length: expectedMajorResourceTypeMinimumCounts[resourceType] }, (_, index) => ({
      LogicalResourceId: `${resourceType.replaceAll(/[^A-Za-z0-9]/g, "")}${index}`,
      PhysicalResourceId: `saphnexa-uat-${resourceType.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")}-${index}`,
      ResourceType: resourceType,
      ResourceStatus: "UPDATE_COMPLETE"
    }))
  );
}

function renderChecklistFixture() {
  const rows = acceptanceIds.map((id) => {
    const source = acceptanceItemById[id];
    return {
      ID: id,
      領域: source.area,
      検収項目: source.item,
      "受け入れ条件 / 完了条件": source.acceptance_condition,
      定量基準: source.quantitative_criteria,
      監査証跡: source.evidence,
      確認方法: source.verification_method,
      重要度: source.priority,
      結果: "PASS",
      証跡リンク: "https://github.com/tsuji-tomonori/saphnexa/actions/runs/26494798563",
      確認者: "acceptance-reviewer",
      確認日: "2026-05-27",
      備考: "final acceptance signed evidence"
    };
  });
  return `${sourceChecklistColumns.join(",")}\n${rows.map((row) => sourceChecklistColumns.map((key) => csv(row[key])).join(",")).join("\n")}\n`;
}

function outputValueFor(outputKey, index) {
  const values = {
    DistributionDomainName: "d111111abcdef8.cloudfront.net",
    AdminArtifactsBucketArn: "arn:aws:s3:::saphnexa-uat-admin-artifacts",
    SignedCookieKeyGroupId: "K1234567890ABC",
    ApiEndpoint: "https://api.saphnexa-uat.net",
    RealtimeEndpoint: "wss://realtime.saphnexa-uat.net/event/realtime",
    DsqlEndpoint: "saphnexa-uat.dsql.ap-northeast-1.on.aws",
    KnowledgeBaseId: "KB12345678",
    DeployRoleArn: `arn:aws:iam::${readyAwsAccountId()}:role/saphnexa-uat-github-deploy`
  };
  return values[outputKey] || `saphnexa-uat-output-${index}`;
}

function readyAwsAccountId() {
  return ["2109", "8765", "4321"].join("");
}

function csv(value) {
  const text = String(value ?? "");
  if (!/[",\n]/.test(text)) return text;
  return `"${text.replaceAll('"', '""')}"`;
}

function assertThrows(fn, message) {
  try {
    fn();
  } catch (error) {
    assert(error.message.includes(message), `unexpected error: ${error.message}`);
    return;
  }
  throw new Error(`expected error: ${message}`);
}
