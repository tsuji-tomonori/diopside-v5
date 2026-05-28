import { assert, readJson } from "./lib.js";

const schema = readJson("docs/acceptance/evidence/evidence_manifest.schema.json");
const manifest = readJson("docs/acceptance/evidence/evidence_manifest.example.json");
const expectedRequired = [
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
const finalAcceptanceExtensionRequired = ["github_release_url", "cdk_app_version"];

assert(schema.$schema === "https://json-schema.org/draft/2020-12/schema", "schema draft mismatch");
assert(schema.title === "Saphnexa Acceptance Evidence Manifest", "schema title mismatch");
assert(schema.x_source?.source_package === "Saphnexa_検収受入条件_package_v1.0", "schema source package mismatch");
assert(schema.x_source?.source_file === "Saphnexa_証跡マニフェスト_schema_v1.0.json", "schema source file mismatch");
assert(schema.x_source?.source_sha256 === "29caa24a6eb0135563cc5a8f690a6837662f5bbdce53c6ee20c328b258e79153", "schema source checksum mismatch");
assert(schema.x_source?.source_target_design === "Saphnexa_基本設計書_v0.16.md", "schema target design mismatch");
assert(JSON.stringify(schema.required) === JSON.stringify(expectedRequired), "schema required fields mismatch");
assert(JSON.stringify(schema.x_final_acceptance_extension?.required) === JSON.stringify(finalAcceptanceExtensionRequired), "schema final acceptance extension required mismatch");
assert(/AC-001/.test(schema.x_final_acceptance_extension?.reason || ""), "schema final acceptance extension reason must cite AC-001");
assert(schema.properties.system.const === "Saphnexa", "schema system const mismatch");
assert(schema.properties.aws_region.const === "ap-northeast-1", "schema region const mismatch");
assert(schema.properties.aws_account_id.pattern === "^[0-9]{12}$", "schema aws account pattern mismatch");
assert(schema.properties.git_commit_sha.pattern === "^[a-f0-9]{40}$", "schema git commit pattern mismatch");
assert(schema.properties.github_release_url.pattern === "^https://github\\.com/.+/releases/tag/.+$", "schema GitHub release URL pattern mismatch");
assert(schema.properties.cdk_app_version.type === "string", "schema CDK app version type mismatch");
assert(schema.properties.test_reports.properties.allure_latest_url.pattern === "^(https://.*/admin/test-reports/allure/latest/|s3://.*/test-reports/allure/latest/).*$", "schema Allure latest URL pattern mismatch");
assert(schema.properties.test_reports.properties.allure_latest_url.description.includes("localhost, private IP"), "schema Allure latest URL description must reject private hosts");
for (const key of ["unit_report_url", "integration_report_url", "e2e_report_url"]) {
  assert(schema.properties.test_reports.properties[key].pattern === "^(https://.*/admin/test-reports/allure/(latest|runs/[^/]+)/|s3://.*/test-reports/allure/(latest|runs/[^/]+)/).*$", `schema ${key} Allure URL pattern mismatch`);
  assert(schema.properties.test_reports.properties[key].description.includes("localhost, private IP"), `schema ${key} description must reject private hosts`);
}
assert(schema.properties.docs_site.properties.latest_url.pattern === "^(https://.*/admin/docs/latest/|s3://.*/docs-site/latest/).*$", "schema docs latest URL pattern mismatch");
assert(schema.properties.docs_site.properties.latest_url.description.includes("localhost, private IP"), "schema docs latest URL description must reject private hosts");
assert(schema.properties.docs_site.properties.version_url.pattern === "^(https://.*/admin/docs/versions/v0\\.16/|s3://.*/docs-site/releases/v0\\.16/).*$", "schema docs version URL pattern mismatch");
assert(schema.properties.docs_site.properties.version_url.description.includes("localhost, private IP"), "schema docs version URL description must reject private hosts");
assert(schema.properties.rag_evaluation.properties.report_url.pattern === "^(https://.*/admin/evaluation-reports/[^/]+/|s3://.*/reports/evaluations/[^/]+/).*$", "schema RAG evaluation report URL pattern mismatch");
assert(schema.properties.rag_evaluation.properties.report_url.description.includes("localhost, private IP"), "schema RAG evaluation report URL description must reject private hosts");
assert(schema.properties.cloudformation_stacks.minItems === 1, "schema CloudFormation stack minItems mismatch");
assert(JSON.stringify(schema.properties.cloudformation_stacks.items.required) === JSON.stringify(["stack_name", "stack_id"]), "schema CloudFormation stack required mismatch");
assert(schema.properties.db_migration.properties.checksum_status.enum.includes("matched"), "schema db checksum enum mismatch");

for (const [section, required] of Object.entries({
  test_reports: ["allure_latest_url", "unit_report_url", "integration_report_url", "e2e_report_url"],
  docs_site: ["latest_url", "version_url"],
  rag_evaluation: ["evaluation_run_id", "report_url"],
  cost_estimate: ["monthly_usd", "assumption"]
})) {
  assert(JSON.stringify(schema.properties[section].required) === JSON.stringify(required), `schema ${section} required mismatch`);
  for (const key of required) {
    assert(schema.properties[section].properties?.[key], `schema ${section}.${key} property missing`);
  }
}

for (const key of schema.required) {
  assert(Object.prototype.hasOwnProperty.call(manifest, key), `manifest missing required field ${key}`);
}
for (const key of schema.x_final_acceptance_extension.required) {
  assert(Object.prototype.hasOwnProperty.call(manifest, key), `manifest missing final extension field ${key}`);
}

assert(manifest.example_status === "example_not_for_acceptance", "example manifest must be marked as not for acceptance");
assert(manifest.system === "Saphnexa", "system must be Saphnexa");
assert(["dev", "uat", "stg", "prod"].includes(manifest.environment), "invalid environment");
assert(manifest.aws_region === "ap-northeast-1", "aws_region must be ap-northeast-1");
assert(/^[0-9]{12}$/.test(manifest.aws_account_id), "aws_account_id must be 12 digits");
assert(/^[a-f0-9]{40}$/.test(manifest.git_commit_sha), "git_commit_sha must be 40 hex chars");
assert(typeof manifest.git_tag === "string" && manifest.git_tag.length > 0, "git_tag is required");
assert(/^https:\/\/github\.com\/.+\/releases\/tag\/.+/.test(manifest.github_release_url), "github_release_url must be a GitHub release URL");
assert(typeof manifest.cdk_app_version === "string" && manifest.cdk_app_version.length > 0, "cdk_app_version is required");
assert(manifest.aws_account_id === "000000000000", "example manifest must use placeholder AWS account id");
assert(/^0{40}$/.test(manifest.git_commit_sha), "example manifest must use placeholder commit SHA");
assert(/example|not-for-acceptance/.test(manifest.git_tag), "example manifest must use non-final tag marker");
assert(/example|not-for-acceptance/.test(manifest.github_release_url), "example manifest must use non-final GitHub release URL marker");
assert(Array.isArray(manifest.cloudformation_stacks) && manifest.cloudformation_stacks.length > 0, "cloudformation_stacks must not be empty");
assert(manifest.db_migration?.checksum_status === "matched", "db migration checksum must be matched");
assert(manifest.cost_estimate?.monthly_usd <= 550, "cost estimate exceeds acceptance limit");
assert(/Final acceptance requires/.test(manifest.cost_estimate?.assumption || ""), "example manifest must state final acceptance limitation");

for (const key of ["allure_latest_url", "unit_report_url", "integration_report_url", "e2e_report_url"]) {
  assert(typeof manifest.test_reports[key] === "string" && manifest.test_reports[key].length > 0, `test_reports.${key} is required`);
  assert(/example/.test(manifest.test_reports[key]), `example test_reports.${key} must be visibly non-final`);
  assert(/\/test-reports\/allure\/(latest|runs\/[^/]+)\//.test(manifest.test_reports[key]), `example test_reports.${key} must use Allure latest or run path`);
}
assert(manifest.test_reports.allure_latest_url.includes("/test-reports/allure/latest/"), "example allure_latest_url must use Allure latest path");
for (const key of ["latest_url", "version_url"]) {
  assert(typeof manifest.docs_site[key] === "string" && manifest.docs_site[key].length > 0, `docs_site.${key} is required`);
  assert(/example/.test(manifest.docs_site[key]), `example docs_site.${key} must be visibly non-final`);
}
assert(manifest.docs_site.latest_url.includes("/docs-site/latest/"), "example docs_site.latest_url must use design docs-site/latest prefix");
assert(manifest.docs_site.version_url.includes("/docs-site/releases/v0.16/"), "example docs_site.version_url must use design docs-site/releases/v0.16 prefix");
assert(/example/.test(manifest.rag_evaluation.evaluation_run_id), "example rag evaluation id must be visibly non-final");
assert(/example/.test(manifest.rag_evaluation.report_url), "example rag evaluation report must be visibly non-final");
assert(manifest.rag_evaluation.report_url.includes(`/reports/evaluations/${manifest.rag_evaluation.evaluation_run_id}/`), "example rag evaluation report must use evaluation report path for evaluation_run_id");

console.log("evidence manifest schema/example check passed (example_not_for_acceptance)");
