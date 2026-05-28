import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { acceptanceIds, acceptanceItemById } from "./acceptance-ids.js";
import { sourceChecklistColumns } from "./acceptance-checklist-format.js";
import { expectedMajorOutputKeys, expectedMajorResourceTypeMinimumCounts, expectedMajorResourceTypes } from "./cloudformation-inventory.js";
import { buildFinalEvidenceCandidateStatus } from "./final-evidence-candidate.js";
import { currentGitCommit } from "./git-context.js";
import { assert } from "./lib.js";

const root = mkdtempSync(join(tmpdir(), "saphnexa-final-candidate-"));

try {
  const resolveGitTagCommit = fixtureGitTagResolver();
  const resolveGitRepository = () => "tsuji-tomonori/saphnexa";
  const readyPaths = writeCandidateFiles(join(root, "ready"), buildReadyCandidate());
  const readyStatus = buildFinalEvidenceCandidateStatus(join(root, "ready-status.json"), { candidatePaths: readyPaths, resolveGitTagCommit, resolveGitRepository });
  assert(readyStatus.ready === true, "ready fixture must be ready");
  assert(readyStatus.status === "ready", "ready fixture status must be ready");
  assert(readyStatus.errors.length === 0, "ready fixture must not have errors");
  assert(readyStatus.checks.some((check) => check.label === "checklist.source_columns" && check.result === "pass"), "ready fixture must check source checklist columns");

  const invalid = buildReadyCandidate();
  invalid.manifest.git_commit_sha = "0123456789abcdef0123456789abcdef01234567";
  invalid.manifest.git_tag = "pending-release-tag";
  invalid.checklistRows[0].結果 = "PENDING_AWS";
  invalid.inventory.source = "local-cdk-intent";
  const invalidPaths = writeCandidateFiles(join(root, "invalid"), invalid);
  const invalidStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-status.json"), { candidatePaths: invalidPaths, resolveGitTagCommit, resolveGitRepository });
  assert(invalidStatus.ready === false, "invalid fixture must not be ready");
  assert(invalidStatus.status === "invalid", "invalid fixture status must be invalid");
  assert(invalidStatus.errors.some((error) => error.includes("manifest.git_commit_sha_current_ref")), "invalid fixture must reject git commit mismatch");
  assert(invalidStatus.errors.some((error) => error.includes("manifest.git_tag")), "invalid fixture must reject pending git tag");
  assert(invalidStatus.errors.some((error) => error.includes("manifest.git_tag_ref")), "invalid fixture must reject missing git tag ref");
  assert(invalidStatus.errors.some((error) => error.includes(`checklist.${acceptanceIds[0]}.結果`)), "invalid fixture must reject non-PASS checklist result");
  assert(invalidStatus.errors.some((error) => error.includes("cloudformation.source")), "invalid fixture must reject non-AWS CloudFormation source");

  const reorderedChecklist = buildReadyCandidate();
  [reorderedChecklist.checklistRows[0], reorderedChecklist.checklistRows[1]] = [reorderedChecklist.checklistRows[1], reorderedChecklist.checklistRows[0]];
  const reorderedChecklistPaths = writeCandidateFiles(join(root, "reordered-checklist"), reorderedChecklist);
  const reorderedChecklistStatus = buildFinalEvidenceCandidateStatus(join(root, "reordered-checklist-status.json"), {
    candidatePaths: reorderedChecklistPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(reorderedChecklistStatus.ready === false, "reordered checklist fixture must not be ready");
  assert(reorderedChecklistStatus.errors.some((error) => error.includes("checklist.source_order")), "reordered checklist fixture must reject source order mismatch");

  const duplicateChecklistId = buildReadyCandidate();
  duplicateChecklistId.checklistRows[1].ID = duplicateChecklistId.checklistRows[0].ID;
  const duplicateChecklistIdPaths = writeCandidateFiles(join(root, "duplicate-checklist-id"), duplicateChecklistId);
  const duplicateChecklistIdStatus = buildFinalEvidenceCandidateStatus(join(root, "duplicate-checklist-id-status.json"), {
    candidatePaths: duplicateChecklistIdPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(duplicateChecklistIdStatus.ready === false, "duplicate checklist ID fixture must not be ready");
  assert(duplicateChecklistIdStatus.errors.some((error) => error.includes("checklist.unique_ids")), "duplicate checklist ID fixture must reject duplicate IDs");

  const mismatchedRelease = buildReadyCandidate();
  mismatchedRelease.manifest.github_release_url = "https://github.com/tsuji-tomonori/saphnexa/releases/tag/v0.16.0-acceptance.2";
  const mismatchedReleasePaths = writeCandidateFiles(join(root, "mismatched-release"), mismatchedRelease);
  const mismatchedReleaseStatus = buildFinalEvidenceCandidateStatus(join(root, "mismatched-release-status.json"), { candidatePaths: mismatchedReleasePaths, resolveGitTagCommit, resolveGitRepository });
  assert(mismatchedReleaseStatus.ready === false, "mismatched release fixture must not be ready");
  assert(mismatchedReleaseStatus.errors.some((error) => error.includes("manifest.github_release_url_git_tag")), "mismatched release fixture must reject release URL tag mismatch");

  const wrongReleaseRepository = buildReadyCandidate();
  wrongReleaseRepository.manifest.github_release_url = "https://github.com/example/saphnexa/releases/tag/v0.16.0-acceptance.1";
  const wrongReleaseRepositoryPaths = writeCandidateFiles(join(root, "wrong-release-repository"), wrongReleaseRepository);
  const wrongReleaseRepositoryStatus = buildFinalEvidenceCandidateStatus(join(root, "wrong-release-repository-status.json"), {
    candidatePaths: wrongReleaseRepositoryPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(wrongReleaseRepositoryStatus.ready === false, "wrong release repository fixture must not be ready");
  assert(wrongReleaseRepositoryStatus.errors.some((error) => error.includes("manifest.github_release_url_repository")), "wrong release repository fixture must reject release repository mismatch");

  const wrongTagCommit = buildReadyCandidate();
  const wrongTagCommitPaths = writeCandidateFiles(join(root, "wrong-tag-commit"), wrongTagCommit);
  const wrongTagCommitStatus = buildFinalEvidenceCandidateStatus(join(root, "wrong-tag-commit-status.json"), {
    candidatePaths: wrongTagCommitPaths,
    resolveGitTagCommit: () => "0123456789abcdef0123456789abcdef01234567",
    resolveGitRepository
  });
  assert(wrongTagCommitStatus.ready === false, "wrong tag commit fixture must not be ready");
  assert(wrongTagCommitStatus.errors.some((error) => error.includes("manifest.git_tag_commit")), "wrong tag commit fixture must reject tag commit mismatch");

  const placeholderAwsAccount = buildReadyCandidate();
  placeholderAwsAccount.manifest.aws_account_id = placeholderAwsAccountId();
  placeholderAwsAccount.manifest.cloudformation_stacks[0].stack_id = placeholderAwsAccount.manifest.cloudformation_stacks[0].stack_id.replace(readyAwsAccountId(), placeholderAwsAccountId());
  placeholderAwsAccount.inventory.stack_id = placeholderAwsAccount.inventory.stack_id.replace(readyAwsAccountId(), placeholderAwsAccountId());
  const placeholderAwsAccountPaths = writeCandidateFiles(join(root, "placeholder-aws-account"), placeholderAwsAccount);
  const placeholderAwsAccountStatus = buildFinalEvidenceCandidateStatus(join(root, "placeholder-aws-account-status.json"), {
    candidatePaths: placeholderAwsAccountPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(placeholderAwsAccountStatus.ready === false, "placeholder AWS account fixture must not be ready");
  assert(placeholderAwsAccountStatus.errors.some((error) => error.includes("manifest.aws_account_id")), "placeholder AWS account fixture must reject common placeholder account id");

  const missingCdkAppVersion = buildReadyCandidate();
  delete missingCdkAppVersion.manifest.cdk_app_version;
  const missingCdkAppVersionPaths = writeCandidateFiles(join(root, "missing-cdk-app-version"), missingCdkAppVersion);
  const missingCdkAppVersionStatus = buildFinalEvidenceCandidateStatus(join(root, "missing-cdk-app-version-status.json"), {
    candidatePaths: missingCdkAppVersionPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(missingCdkAppVersionStatus.ready === false, "missing CDK app version fixture must not be ready");
  assert(missingCdkAppVersionStatus.errors.some((error) => error === "manifest.cdk_app_version: required"), "missing CDK app version fixture must reject missing required field");

  const mismatchedCdkAppVersion = buildReadyCandidate();
  mismatchedCdkAppVersion.manifest.cdk_app_version = "9.9.9";
  const mismatchedCdkAppVersionPaths = writeCandidateFiles(join(root, "mismatched-cdk-app-version"), mismatchedCdkAppVersion);
  const mismatchedCdkAppVersionStatus = buildFinalEvidenceCandidateStatus(join(root, "mismatched-cdk-app-version-status.json"), {
    candidatePaths: mismatchedCdkAppVersionPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(mismatchedCdkAppVersionStatus.ready === false, "mismatched CDK app version fixture must not be ready");
  assert(mismatchedCdkAppVersionStatus.errors.some((error) => error.includes("manifest.cdk_app_version_package_version")), "mismatched CDK app version fixture must reject package version mismatch");

  const invalidRequiredValues = buildReadyCandidate();
  invalidRequiredValues.manifest.cdk_app_version = "";
  invalidRequiredValues.manifest.db_migration.tool = "Liquibase";
  invalidRequiredValues.manifest.db_migration.latest_version = "draft-migration-version";
  invalidRequiredValues.manifest.cost_estimate.assumption = "pending cost estimate";
  const invalidRequiredValuesPaths = writeCandidateFiles(join(root, "invalid-required-values"), invalidRequiredValues);
  const invalidRequiredValuesStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-required-values-status.json"), {
    candidatePaths: invalidRequiredValuesPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidRequiredValuesStatus.ready === false, "invalid required values fixture must not be ready");
  assert(invalidRequiredValuesStatus.errors.some((error) => error.includes("manifest.cdk_app_version")), "invalid required values fixture must reject empty CDK app version");
  assert(invalidRequiredValuesStatus.errors.some((error) => error.includes("manifest.db_migration.tool")), "invalid required values fixture must reject non-Flyway migration tool");
  assert(invalidRequiredValuesStatus.errors.some((error) => error.includes("manifest.db_migration.latest_version")), "invalid required values fixture must reject draft DB migration version");
  assert(invalidRequiredValuesStatus.errors.some((error) => error.includes("manifest.cost_estimate.assumption")), "invalid required values fixture must reject pending cost assumption");

  const draftArtifactUrlMarker = buildReadyCandidate();
  draftArtifactUrlMarker.manifest.test_reports.unit_report_url = "s3://saphnexa-uat-admin-artifacts/draft/test-reports/allure/runs/unit-20260527/";
  const draftArtifactUrlMarkerPaths = writeCandidateFiles(join(root, "draft-artifact-url-marker"), draftArtifactUrlMarker);
  const draftArtifactUrlMarkerStatus = buildFinalEvidenceCandidateStatus(join(root, "draft-artifact-url-marker-status.json"), {
    candidatePaths: draftArtifactUrlMarkerPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(draftArtifactUrlMarkerStatus.ready === false, "draft artifact URL marker fixture must not be ready");
  assert(draftArtifactUrlMarkerStatus.errors.some((error) => error.includes("manifest.no_forbidden_markers.test_reports.unit_report_url")), "draft artifact URL marker fixture must reject draft marker inside URL");
  assert(draftArtifactUrlMarkerStatus.errors.some((error) => error.includes("manifest.test_reports.unit_report_url")), "draft artifact URL marker fixture must reject URL with draft marker");

  const mismatchedDbMigrationVersion = buildReadyCandidate();
  mismatchedDbMigrationVersion.manifest.db_migration.latest_version = "V999__wrong_schema.sql";
  const mismatchedDbMigrationVersionPaths = writeCandidateFiles(join(root, "mismatched-db-migration-version"), mismatchedDbMigrationVersion);
  const mismatchedDbMigrationVersionStatus = buildFinalEvidenceCandidateStatus(join(root, "mismatched-db-migration-version-status.json"), {
    candidatePaths: mismatchedDbMigrationVersionPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(mismatchedDbMigrationVersionStatus.ready === false, "mismatched DB migration version fixture must not be ready");
  assert(mismatchedDbMigrationVersionStatus.errors.some((error) => error.includes("manifest.db_migration.latest_version_latest_file")), "mismatched DB migration version fixture must reject latest migration file mismatch");

  const invalidDocsSiteUrls = buildReadyCandidate();
  invalidDocsSiteUrls.manifest.docs_site.latest_url = "s3://saphnexa-acceptance-artifacts/docs/current/";
  invalidDocsSiteUrls.manifest.docs_site.version_url = "s3://saphnexa-acceptance-artifacts/docs/versions/v0.15/";
  const invalidDocsSiteUrlsPaths = writeCandidateFiles(join(root, "invalid-docs-site-urls"), invalidDocsSiteUrls);
  const invalidDocsSiteUrlsStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-docs-site-urls-status.json"), {
    candidatePaths: invalidDocsSiteUrlsPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidDocsSiteUrlsStatus.ready === false, "invalid docs site URLs fixture must not be ready");
  assert(invalidDocsSiteUrlsStatus.errors.some((error) => error.includes("manifest.docs_site.latest_url_admin_docs_path")), "invalid docs site URLs fixture must reject non-latest docs path");
  assert(invalidDocsSiteUrlsStatus.errors.some((error) => error.includes("manifest.docs_site.version_url_admin_docs_path")), "invalid docs site URLs fixture must reject non-v0.16 docs version path");

  const invalidDocsSitePrefixes = buildReadyCandidate();
  invalidDocsSitePrefixes.manifest.docs_site.latest_url = "s3://saphnexa-acceptance-artifacts/docs/latest/";
  invalidDocsSitePrefixes.manifest.docs_site.version_url = "s3://saphnexa-acceptance-artifacts/docs/versions/v0.16/";
  const invalidDocsSitePrefixesPaths = writeCandidateFiles(join(root, "invalid-docs-site-prefixes"), invalidDocsSitePrefixes);
  const invalidDocsSitePrefixesStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-docs-site-prefixes-status.json"), {
    candidatePaths: invalidDocsSitePrefixesPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidDocsSitePrefixesStatus.ready === false, "invalid docs site prefixes fixture must not be ready");
  assert(invalidDocsSitePrefixesStatus.errors.some((error) => error.includes("manifest.docs_site.latest_url_admin_docs_path")), "invalid docs site prefixes fixture must reject non-design latest docs prefix");
  assert(invalidDocsSitePrefixesStatus.errors.some((error) => error.includes("manifest.docs_site.version_url_admin_docs_path")), "invalid docs site prefixes fixture must reject non-design version docs prefix");

  const invalidAllureReportUrl = buildReadyCandidate();
  invalidAllureReportUrl.manifest.test_reports.allure_latest_url = "s3://saphnexa-acceptance-artifacts/test-reports/unit/latest/";
  const invalidAllureReportUrlPaths = writeCandidateFiles(join(root, "invalid-allure-report-url"), invalidAllureReportUrl);
  const invalidAllureReportUrlStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-allure-report-url-status.json"), {
    candidatePaths: invalidAllureReportUrlPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidAllureReportUrlStatus.ready === false, "invalid Allure report URL fixture must not be ready");
  assert(invalidAllureReportUrlStatus.errors.some((error) => error.includes("manifest.test_reports.allure_latest_url_latest_path")), "invalid Allure report URL fixture must reject non-Allure latest path");

  const invalidLayeredTestReportUrls = buildReadyCandidate();
  invalidLayeredTestReportUrls.manifest.test_reports.unit_report_url = "s3://saphnexa-acceptance-artifacts/test-reports/unit/latest/";
  invalidLayeredTestReportUrls.manifest.test_reports.integration_report_url = "s3://saphnexa-acceptance-artifacts/test-reports/integration/latest/";
  invalidLayeredTestReportUrls.manifest.test_reports.e2e_report_url = "s3://saphnexa-acceptance-artifacts/test-reports/e2e/latest/";
  const invalidLayeredTestReportUrlsPaths = writeCandidateFiles(join(root, "invalid-layered-test-report-urls"), invalidLayeredTestReportUrls);
  const invalidLayeredTestReportUrlsStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-layered-test-report-urls-status.json"), {
    candidatePaths: invalidLayeredTestReportUrlsPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidLayeredTestReportUrlsStatus.ready === false, "invalid layered test report URLs fixture must not be ready");
  for (const key of ["unit_report_url", "integration_report_url", "e2e_report_url"]) {
    assert(invalidLayeredTestReportUrlsStatus.errors.some((error) => error.includes(`manifest.test_reports.${key}_allure_path`)), `invalid layered test report URLs fixture must reject ${key}`);
  }

  const missingCostUsageBasis = buildReadyCandidate();
  missingCostUsageBasis.manifest.cost_estimate.assumption = "UAT estimate using approved acceptance usage basis.";
  const missingCostUsageBasisPaths = writeCandidateFiles(join(root, "missing-cost-usage-basis"), missingCostUsageBasis);
  const missingCostUsageBasisStatus = buildFinalEvidenceCandidateStatus(join(root, "missing-cost-usage-basis-status.json"), {
    candidatePaths: missingCostUsageBasisPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(missingCostUsageBasisStatus.ready === false, "missing cost usage basis fixture must not be ready");
  assert(missingCostUsageBasisStatus.errors.some((error) => error.includes("manifest.cost_estimate.assumption_usage_basis")), "missing cost usage basis fixture must reject missing usage basis");

  const privateArtifactUrls = buildReadyCandidate();
  privateArtifactUrls.manifest.docs_site.latest_url = "https://docs.saphnexa-uat.internal/admin/docs/latest/";
  privateArtifactUrls.manifest.test_reports.allure_latest_url = "https://localhost/admin/test-reports/allure/latest/";
  privateArtifactUrls.manifest.test_reports.unit_report_url = "https://reports.saphnexa.local/admin/test-reports/allure/runs/unit-20260527/";
  privateArtifactUrls.manifest.test_reports.integration_report_url = "https://reports.saphnexa.test/admin/test-reports/allure/runs/integration-20260527/";
  privateArtifactUrls.manifest.rag_evaluation.report_url = "https://192.168.10.10/admin/evaluation-reports/eval-20260527-uat-final/";
  privateArtifactUrls.checklistRows[0].証跡リンク = "https://127.0.0.1/actions/runs/26494798563";
  const privateArtifactUrlsPaths = writeCandidateFiles(join(root, "private-artifact-urls"), privateArtifactUrls);
  const privateArtifactUrlsStatus = buildFinalEvidenceCandidateStatus(join(root, "private-artifact-urls-status.json"), {
    candidatePaths: privateArtifactUrlsPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(privateArtifactUrlsStatus.ready === false, "private artifact URL fixture must not be ready");
  assert(privateArtifactUrlsStatus.errors.some((error) => error.includes("manifest.docs_site.latest_url")), "private artifact URL fixture must reject internal docs URL");
  assert(privateArtifactUrlsStatus.errors.some((error) => error.includes("manifest.test_reports.allure_latest_url")), "private artifact URL fixture must reject localhost Allure URL");
  assert(privateArtifactUrlsStatus.errors.some((error) => error.includes("manifest.test_reports.unit_report_url")), "private artifact URL fixture must reject .local Allure URL");
  assert(privateArtifactUrlsStatus.errors.some((error) => error.includes("manifest.test_reports.integration_report_url")), "private artifact URL fixture must reject .test Allure URL");
  assert(privateArtifactUrlsStatus.errors.some((error) => error.includes("manifest.rag_evaluation.report_url")), "private artifact URL fixture must reject private IP evaluation report URL");
  assert(privateArtifactUrlsStatus.errors.some((error) => error.includes(`checklist.${acceptanceIds[0]}.証跡リンク_url`)), "private artifact URL fixture must reject private checklist evidence URL");

  const unknownArtifactDeploymentSource = buildReadyCandidate();
  unknownArtifactDeploymentSource.manifest.docs_site.latest_url = "https://artifacts.othercorp.net/admin/docs/latest/";
  unknownArtifactDeploymentSource.manifest.test_reports.allure_latest_url = "s3://othercorp-acceptance-artifacts/test-reports/allure/latest/";
  const unknownArtifactDeploymentSourcePaths = writeCandidateFiles(join(root, "unknown-artifact-deployment-source"), unknownArtifactDeploymentSource);
  const unknownArtifactDeploymentSourceStatus = buildFinalEvidenceCandidateStatus(join(root, "unknown-artifact-deployment-source-status.json"), {
    candidatePaths: unknownArtifactDeploymentSourcePaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(unknownArtifactDeploymentSourceStatus.ready === false, "unknown artifact deployment source fixture must not be ready");
  assert(unknownArtifactDeploymentSourceStatus.errors.some((error) => error.includes("final_evidence.artifact_deployment_source.docs_site.latest_url")), "unknown artifact deployment source fixture must reject docs URL outside CloudFormation outputs");
  assert(unknownArtifactDeploymentSourceStatus.errors.some((error) => error.includes("final_evidence.artifact_deployment_source.test_reports.allure_latest_url")), "unknown artifact deployment source fixture must reject Allure URL outside CloudFormation outputs");

  const unknownChecklistEvidenceSource = buildReadyCandidate();
  unknownChecklistEvidenceSource.checklistRows[0].証跡リンク = "https://evidence.othercorp.net/admin/docs/latest/";
  const unknownChecklistEvidenceSourcePaths = writeCandidateFiles(join(root, "unknown-checklist-evidence-source"), unknownChecklistEvidenceSource);
  const unknownChecklistEvidenceSourceStatus = buildFinalEvidenceCandidateStatus(join(root, "unknown-checklist-evidence-source-status.json"), {
    candidatePaths: unknownChecklistEvidenceSourcePaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(unknownChecklistEvidenceSourceStatus.ready === false, "unknown checklist evidence source fixture must not be ready");
  assert(unknownChecklistEvidenceSourceStatus.errors.some((error) => error.includes(`checklist.${acceptanceIds[0]}.証跡リンク_known_source`)), "unknown checklist evidence source fixture must reject evidence outside manifest locations and current repository");

  const mismatchedRagEvaluationReport = buildReadyCandidate();
  mismatchedRagEvaluationReport.manifest.rag_evaluation.report_url = "s3://saphnexa-acceptance-artifacts/reports/evaluations/eval-other-run/";
  const mismatchedRagEvaluationReportPaths = writeCandidateFiles(join(root, "mismatched-rag-evaluation-report"), mismatchedRagEvaluationReport);
  const mismatchedRagEvaluationReportStatus = buildFinalEvidenceCandidateStatus(join(root, "mismatched-rag-evaluation-report-status.json"), {
    candidatePaths: mismatchedRagEvaluationReportPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(mismatchedRagEvaluationReportStatus.ready === false, "mismatched RAG evaluation report fixture must not be ready");
  assert(mismatchedRagEvaluationReportStatus.errors.some((error) => error.includes("manifest.rag_evaluation.report_url_evaluation_run")), "mismatched RAG evaluation report fixture must reject report URL that does not match evaluation_run_id");

  for (const [fixtureName, monthlyUsd, message] of [
    ["null-cost", null, "null cost estimate"],
    ["negative-cost", -1, "negative cost estimate"],
    ["excess-cost", 550.01, "excess cost estimate"]
  ]) {
    const invalidCostEstimate = buildReadyCandidate();
    invalidCostEstimate.manifest.cost_estimate.monthly_usd = monthlyUsd;
    const invalidCostEstimatePaths = writeCandidateFiles(join(root, fixtureName), invalidCostEstimate);
    const invalidCostEstimateStatus = buildFinalEvidenceCandidateStatus(join(root, `${fixtureName}-status.json`), {
      candidatePaths: invalidCostEstimatePaths,
      resolveGitTagCommit,
      resolveGitRepository
    });
    assert(invalidCostEstimateStatus.ready === false, `${message} fixture must not be ready`);
    assert(invalidCostEstimateStatus.errors.some((error) => error.includes("manifest.cost_estimate.monthly_usd")), `${message} fixture must reject invalid monthly_usd`);
  }

  const mismatchedInventory = buildReadyCandidate();
  mismatchedInventory.inventory.stack_id = "arn:aws:cloudformation:ap-northeast-1:999999999999:stack/saphnexa-other-app/abc12345";
  mismatchedInventory.inventory.stack_name = "saphnexa-other-app";
  const mismatchedInventoryPaths = writeCandidateFiles(join(root, "mismatched-inventory"), mismatchedInventory);
  const mismatchedInventoryStatus = buildFinalEvidenceCandidateStatus(join(root, "mismatched-inventory-status.json"), {
    candidatePaths: mismatchedInventoryPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(mismatchedInventoryStatus.ready === false, "mismatched inventory fixture must not be ready");
  assert(mismatchedInventoryStatus.errors.some((error) => error.includes("final_evidence.aws_account_consistency")), "mismatched inventory fixture must reject AWS account mismatch");
  assert(mismatchedInventoryStatus.errors.some((error) => error.includes("final_evidence.stack_id_consistency")), "mismatched inventory fixture must reject stack id mismatch");
  assert(mismatchedInventoryStatus.errors.some((error) => error.includes("final_evidence.stack_name_consistency")), "mismatched inventory fixture must reject stack name mismatch");

  const missingMajorResource = buildReadyCandidate();
  missingMajorResource.inventory.stack_resources = missingMajorResource.inventory.stack_resources.filter((resource) => resource.ResourceType !== expectedMajorResourceTypes[0]);
  const missingMajorResourcePaths = writeCandidateFiles(join(root, "missing-major-resource"), missingMajorResource);
  const missingMajorResourceStatus = buildFinalEvidenceCandidateStatus(join(root, "missing-major-resource-status.json"), {
    candidatePaths: missingMajorResourcePaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(missingMajorResourceStatus.ready === false, "missing major resource fixture must not be ready");
  assert(missingMajorResourceStatus.errors.some((error) => error.includes(`cloudformation.major_resource_type.${expectedMajorResourceTypes[0]}`)), "missing major resource fixture must reject missing expected resource type");

  const insufficientMajorResourceCount = buildReadyCandidate();
  const resourceTypeWithMinimumCount = "AWS::Lambda::Function";
  insufficientMajorResourceCount.inventory.stack_resources = insufficientMajorResourceCount.inventory.stack_resources.filter((resource, index) => resource.ResourceType !== resourceTypeWithMinimumCount || index === insufficientMajorResourceCount.inventory.stack_resources.findIndex((item) => item.ResourceType === resourceTypeWithMinimumCount));
  const insufficientMajorResourceCountPaths = writeCandidateFiles(join(root, "insufficient-major-resource-count"), insufficientMajorResourceCount);
  const insufficientMajorResourceCountStatus = buildFinalEvidenceCandidateStatus(join(root, "insufficient-major-resource-count-status.json"), {
    candidatePaths: insufficientMajorResourceCountPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(insufficientMajorResourceCountStatus.ready === false, "insufficient major resource count fixture must not be ready");
  assert(insufficientMajorResourceCountStatus.errors.some((error) => error.includes(`cloudformation.major_resource_type_count.${resourceTypeWithMinimumCount}`)), "insufficient major resource count fixture must reject expected minimum count mismatch");

  const invalidResourceDetails = buildReadyCandidate();
  delete invalidResourceDetails.inventory.stack_resources[0].LogicalResourceId;
  invalidResourceDetails.inventory.stack_resources[1].PhysicalResourceId = "";
  invalidResourceDetails.inventory.stack_resources[2].ResourceStatus = "UPDATE_IN_PROGRESS";
  const invalidResourceDetailsPaths = writeCandidateFiles(join(root, "invalid-resource-details"), invalidResourceDetails);
  const invalidResourceDetailsStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-resource-details-status.json"), {
    candidatePaths: invalidResourceDetailsPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidResourceDetailsStatus.ready === false, "invalid resource details fixture must not be ready");
  assert(invalidResourceDetailsStatus.errors.some((error) => error.includes(`cloudformation.resource.${expectedMajorResourceTypes[0]}.LogicalResourceId`)), "invalid resource details fixture must reject missing logical resource id");
  assert(invalidResourceDetailsStatus.errors.some((error) => error.includes("PhysicalResourceId")), "invalid resource details fixture must reject missing physical resource id");
  assert(invalidResourceDetailsStatus.errors.some((error) => error.includes("ResourceStatus")), "invalid resource details fixture must reject non-complete resource status");

  const invalidStackStatusOutputs = buildReadyCandidate();
  invalidStackStatusOutputs.inventory.stack_status = "ROLLBACK_COMPLETE";
  invalidStackStatusOutputs.inventory.stack_outputs = [];
  const invalidStackStatusOutputsPaths = writeCandidateFiles(join(root, "invalid-stack-status-outputs"), invalidStackStatusOutputs);
  const invalidStackStatusOutputsStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-stack-status-outputs-status.json"), {
    candidatePaths: invalidStackStatusOutputsPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidStackStatusOutputsStatus.ready === false, "invalid stack status outputs fixture must not be ready");
  assert(invalidStackStatusOutputsStatus.errors.some((error) => error.includes("cloudformation.stack_status")), "invalid stack status outputs fixture must reject rollback stack status");
  assert(invalidStackStatusOutputsStatus.errors.some((error) => error.includes("cloudformation.stack_outputs")), "invalid stack status outputs fixture must reject empty stack outputs");

  const missingCaptureEvidence = buildReadyCandidate();
  delete missingCaptureEvidence.inventory.capture_evidence;
  const missingCaptureEvidencePaths = writeCandidateFiles(join(root, "missing-capture-evidence"), missingCaptureEvidence);
  const missingCaptureEvidenceStatus = buildFinalEvidenceCandidateStatus(join(root, "missing-capture-evidence-status.json"), {
    candidatePaths: missingCaptureEvidencePaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(missingCaptureEvidenceStatus.ready === false, "missing capture evidence fixture must not be ready");
  assert(missingCaptureEvidenceStatus.errors.some((error) => error.includes("cloudformation.capture_evidence")), "missing capture evidence fixture must reject missing capture metadata");

  const invalidCaptureEvidence = buildReadyCandidate();
  invalidCaptureEvidence.inventory.capture_evidence.captured_at = "2026-02-30T00:00:00+09:00";
  invalidCaptureEvidence.inventory.capture_evidence.describe_stacks_command = "aws cloudformation describe-stack-events --stack-name saphnexa-uat-app --region ap-northeast-1 --output json";
  invalidCaptureEvidence.inventory.capture_evidence.list_stack_resources_command = "aws cloudformation list-stack-resources --stack-name saphnexa-other-app --region ap-northeast-1 --output json";
  const invalidCaptureEvidencePaths = writeCandidateFiles(join(root, "invalid-capture-evidence"), invalidCaptureEvidence);
  const invalidCaptureEvidenceStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-capture-evidence-status.json"), {
    candidatePaths: invalidCaptureEvidencePaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidCaptureEvidenceStatus.ready === false, "invalid capture evidence fixture must not be ready");
  assert(invalidCaptureEvidenceStatus.errors.some((error) => error.includes("cloudformation.capture_evidence.captured_at")), "invalid capture evidence fixture must reject invalid timestamp");
  assert(invalidCaptureEvidenceStatus.errors.some((error) => error.includes("cloudformation.capture_evidence.describe_stacks_command")), "invalid capture evidence fixture must reject wrong describe command");
  assert(invalidCaptureEvidenceStatus.errors.some((error) => error.includes("cloudformation.capture_evidence.list_stack_resources_command")), "invalid capture evidence fixture must reject wrong stack resource command");

  const missingMajorOutput = buildReadyCandidate();
  missingMajorOutput.inventory.stack_outputs = missingMajorOutput.inventory.stack_outputs.filter((output) => output.OutputKey !== expectedMajorOutputKeys[0]);
  const missingMajorOutputPaths = writeCandidateFiles(join(root, "missing-major-output"), missingMajorOutput);
  const missingMajorOutputStatus = buildFinalEvidenceCandidateStatus(join(root, "missing-major-output-status.json"), {
    candidatePaths: missingMajorOutputPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(missingMajorOutputStatus.ready === false, "missing major output fixture must not be ready");
  assert(missingMajorOutputStatus.errors.some((error) => error.includes(`cloudformation.major_output_key.${expectedMajorOutputKeys[0]}`)), "missing major output fixture must reject missing expected output key");

  const invalidManifestStacks = buildReadyCandidate();
  invalidManifestStacks.manifest.cloudformation_stacks.push(
    {
      stack_name: "saphnexa-uat-wrong-account",
      stack_id: "arn:aws:cloudformation:ap-northeast-1:999999999999:stack/saphnexa-uat-wrong-account/abc12345"
    },
    {
      stack_name: "saphnexa-uat-wrong-region",
      stack_id: "arn:aws:cloudformation:us-east-1:123456789012:stack/saphnexa-uat-wrong-region/abc12345"
    },
    {
      stack_name: "saphnexa-uat-declared-name",
      stack_id: "arn:aws:cloudformation:ap-northeast-1:123456789012:stack/saphnexa-uat-actual-name/abc12345"
    }
  );
  const invalidManifestStacksPaths = writeCandidateFiles(join(root, "invalid-manifest-stacks"), invalidManifestStacks);
  const invalidManifestStacksStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-manifest-stacks-status.json"), {
    candidatePaths: invalidManifestStacksPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidManifestStacksStatus.ready === false, "invalid manifest stacks fixture must not be ready");
  assert(invalidManifestStacksStatus.errors.some((error) => error.includes("manifest.cloudformation_stacks.saphnexa-uat-wrong-account.stack_account")), "invalid manifest stacks fixture must reject stack account mismatch");
  assert(invalidManifestStacksStatus.errors.some((error) => error.includes("manifest.cloudformation_stacks.saphnexa-uat-wrong-region.stack_region")), "invalid manifest stacks fixture must reject stack region mismatch");
  assert(invalidManifestStacksStatus.errors.some((error) => error.includes("manifest.cloudformation_stacks.saphnexa-uat-declared-name.stack_name_arn")), "invalid manifest stacks fixture must reject stack name ARN mismatch");

  const invalidChecklistValues = buildReadyCandidate();
  invalidChecklistValues.checklistRows[0].証跡リンク = "manual evidence attached";
  invalidChecklistValues.checklistRows[1].確認者 = "pending-final-acceptance";
  invalidChecklistValues.checklistRows[2].確認日 = "2026-02-30";
  const invalidChecklistValuesPaths = writeCandidateFiles(join(root, "invalid-checklist-values"), invalidChecklistValues);
  const invalidChecklistValuesStatus = buildFinalEvidenceCandidateStatus(join(root, "invalid-checklist-values-status.json"), {
    candidatePaths: invalidChecklistValuesPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(invalidChecklistValuesStatus.ready === false, "invalid checklist values fixture must not be ready");
  assert(invalidChecklistValuesStatus.errors.some((error) => error.includes(`checklist.${acceptanceIds[0]}.証跡リンク_url`)), "invalid checklist values fixture must reject non-URL evidence link");
  assert(invalidChecklistValuesStatus.errors.some((error) => error.includes(`checklist.${acceptanceIds[1]}.確認者`)), "invalid checklist values fixture must reject pending reviewer");
  assert(invalidChecklistValuesStatus.errors.some((error) => error.includes(`checklist.${acceptanceIds[2]}.確認日_date`)), "invalid checklist values fixture must reject invalid checked date");

  const checklistForbiddenMarker = buildReadyCandidate();
  checklistForbiddenMarker.checklistRows[4].備考 = "draft final signoff note";
  const checklistForbiddenMarkerPaths = writeCandidateFiles(join(root, "checklist-forbidden-marker"), checklistForbiddenMarker);
  const checklistForbiddenMarkerStatus = buildFinalEvidenceCandidateStatus(join(root, "checklist-forbidden-marker-status.json"), {
    candidatePaths: checklistForbiddenMarkerPaths,
    resolveGitTagCommit,
    resolveGitRepository
  });
  assert(checklistForbiddenMarkerStatus.ready === false, "checklist forbidden marker fixture must not be ready");
  assert(checklistForbiddenMarkerStatus.errors.some((error) => error.includes(`checklist.${acceptanceIds[4]}.no_forbidden_markers`)), "checklist forbidden marker fixture must reject draft marker in note");

  const futureChecklistDate = buildReadyCandidate();
  futureChecklistDate.checklistRows[3].確認日 = "2999-01-01";
  const futureChecklistDatePaths = writeCandidateFiles(join(root, "future-checklist-date"), futureChecklistDate);
  const futureChecklistDateStatus = buildFinalEvidenceCandidateStatus(join(root, "future-checklist-date-status.json"), {
    candidatePaths: futureChecklistDatePaths,
    resolveGitTagCommit,
    resolveGitRepository,
    currentDate: "2026-05-27"
  });
  assert(futureChecklistDateStatus.ready === false, "future checklist date fixture must not be ready");
  assert(futureChecklistDateStatus.errors.some((error) => error.includes(`checklist.${acceptanceIds[3]}.確認日_not_future`)), "future checklist date fixture must reject future checked date");

  console.log("final evidence candidate fixture check passed");
} finally {
  rmSync(root, { recursive: true, force: true });
}

function fixtureGitTagResolver() {
  const gitCommit = currentGitCommit();
  return (tagName) => {
    if (tagName === "v0.16.0-acceptance.1") return gitCommit;
    return null;
  };
}

function buildReadyCandidate() {
  const accountId = readyAwsAccountId();
  const stackId = `arn:aws:cloudformation:ap-northeast-1:${accountId}:stack/saphnexa-uat-app/abc12345`;
  return {
    manifest: {
      system: "Saphnexa",
      environment: "uat",
      aws_region: "ap-northeast-1",
      aws_account_id: accountId,
      git_commit_sha: currentGitCommit(),
      git_tag: "v0.16.0-acceptance.1",
      github_release_url: "https://github.com/tsuji-tomonori/saphnexa/releases/tag/v0.16.0-acceptance.1",
      cdk_app_version: "0.1.0",
      cloudformation_stacks: [
        {
          stack_name: "saphnexa-uat-app",
          stack_id: stackId
        }
      ],
      db_migration: {
        tool: "Flyway",
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
    },
    checklistRows: acceptanceIds.map((id) => {
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
        備考: "fixture-final-validator-coverage"
      };
    }),
    inventory: {
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
      stack_outputs: [
        ...expectedMajorOutputKeys.map((outputKey, index) => ({
          OutputKey: outputKey,
          OutputValue: outputValueFor(outputKey, index)
        }))
      ],
      stack_resources: expectedMajorResources()
    }
  };
}

function expectedMajorResources() {
  return expectedMajorResourceTypes.flatMap((resourceType) => {
    const count = expectedMajorResourceTypeMinimumCounts[resourceType];
    return Array.from({ length: count }, (_, index) => ({
      LogicalResourceId: `${resourceType.replaceAll(/[^A-Za-z0-9]/g, "")}${index}`,
      PhysicalResourceId: `saphnexa-uat-${resourceType.toLowerCase().replaceAll(/[^a-z0-9]+/g, "-")}-${index}`,
      ResourceType: resourceType,
      ResourceStatus: "UPDATE_COMPLETE"
    }));
  });
}

function outputValueFor(outputKey, index) {
  const values = {
    DistributionDomainName: "d111111abcdef8.cloudfront.net",
    AdminArtifactsBucketArn: "arn:aws:s3:::saphnexa-uat-admin-artifacts",
    SignedCookieKeyGroupId: "K1234567890ABC",
    ApiEndpoint: "https://api.saphnexa-uat.internal",
    RealtimeEndpoint: "wss://realtime.saphnexa-uat.internal/event/realtime",
    DsqlEndpoint: "saphnexa-uat.dsql.ap-northeast-1.on.aws",
    KnowledgeBaseId: "KB12345678",
    DeployRoleArn: `arn:aws:iam::${readyAwsAccountId()}:role/saphnexa-uat-github-deploy`
  };
  return values[outputKey] || `saphnexa-uat-output-${index}`;
}

function readyAwsAccountId() {
  return ["2109", "8765", "4321"].join("");
}

function placeholderAwsAccountId() {
  return ["1234", "5678", "9012"].join("");
}

function writeCandidateFiles(dir, candidate) {
  mkdirSync(dir, { recursive: true });
  const paths = {
    evidence_manifest: join(dir, "evidence_manifest.json"),
    acceptance_checklist: join(dir, "acceptance_checklist.csv"),
    cloudformation_inventory: join(dir, "cloudformation_inventory.uat.json")
  };
  writeFileSync(paths.evidence_manifest, `${JSON.stringify(candidate.manifest, null, 2)}\n`);
  writeFileSync(paths.acceptance_checklist, renderCsv(candidate.checklistRows));
  writeFileSync(paths.cloudformation_inventory, `${JSON.stringify(candidate.inventory, null, 2)}\n`);
  return paths;
}

function renderCsv(rows) {
  return `${sourceChecklistColumns.join(",")}\n${rows.map((row) => sourceChecklistColumns.map((key) => csv(row[key])).join(",")).join("\n")}\n`;
}

function csv(value) {
  const text = String(value ?? "");
  return /[",\n]/.test(text) ? `"${text.replaceAll("\"", "\"\"")}"` : text;
}
