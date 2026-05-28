import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { currentJstTimestamp, readJson, readText } from "./lib.js";

const outputRoot = "dist/admin/test-reports/allure/latest";
const generatedAt = currentJstTimestamp();
const packageJson = readJson("package.json");
const workflow = readText(".github/workflows/ci.yml");
const suites = [
  suite("unit", "npm test"),
  suite("integration", "npm run test:integration:local"),
  suite("e2e", "npm run test:e2e:local"),
  suite("contract", "npm run test:contract"),
  suite("cloudformation-inventory-build", "npm run cfn:inventory:build"),
  suite("cloudformation-inventory-check", "npm run cfn:inventory:check"),
  suite("edge-security", "npm run edge:security:check"),
  suite("coverage", "npm run coverage:check"),
  suite("ui-quality", "npm run ui:check"),
  suite("web-flow", "npm run web:flow:check"),
  suite("web-a11y", "npm run web:a11y:check"),
  suite("web-performance", "npm run web:perf:local"),
  suite("web-bundle", "npm run web:bundle:check"),
  suite("api-performance", "npm run perf:api:local"),
  suite("failure-injection", "npm run failure:check"),
  suite("rag-quality", "npm run rag:quality:check"),
  suite("rag-security", "npm run rag:security:check"),
  suite("rag-performance", "npm run rag:perf:local"),
  suite("db-migration", "npm run db:migration:check"),
  suite("db-integrity", "npm run db:integrity:check"),
  suite("local-search", "npm run search:local:check"),
  suite("observability", "npm run observability:check"),
  suite("admin-workflow", "npm run admin:workflow:check"),
  suite("offline-artifacts", "npm run offline-artifacts:check"),
  suite("restore-drill", "npm run restore:drill:check"),
  suite("acceptance-source", "npm run acceptance:source:check"),
  suite("acceptance", "npm run acceptance:check"),
  suite("evidence", "npm run evidence:check"),
  suite("acceptance-external-actions-build", "npm run acceptance:external-actions:build"),
  suite("acceptance-external-actions-check", "npm run acceptance:external-actions:check"),
  suite("acceptance-final-candidate-fixture", "npm run acceptance:final-candidate:fixture:check"),
  suite("acceptance-final-fixture", "npm run acceptance:final:fixture:check"),
  suite("acceptance-final-candidate", "npm run acceptance:final-candidate:check"),
  suite("acceptance-final-build", "npm run acceptance:final:build"),
  suite("acceptance-final-check", "npm run acceptance:final:check"),
  suite("acceptance-package-build", "npm run acceptance:package:build"),
  suite("acceptance-package-check", "npm run acceptance:package:check"),
  suite("admin-artifacts", "npm run artifacts:check")
];

rmSync(outputRoot, { recursive: true, force: true });

const html = renderReport(suites);
const indexPath = join(outputRoot, "index.html");
write(indexPath, html);

const manifest = {
  schema_version: "admin-test-report-artifact.v1",
  generated_by: "tools/build-admin-test-report.js",
  artifact_id: "admin-allure-latest",
  artifact_type: "allure_report",
  title: "Allure 互換ローカル検証レポート latest",
  viewer_path: "/admin/test-reports/allure/latest/",
  index_path: indexPath,
  status: "published-local",
  source_files: ["package.json", ".github/workflows/ci.yml", "tests/contract.test.js", "tests/integration-local.test.js", "tests/e2e-local.test.js"],
  suites,
  checksum: `sha256:${sha256(html)}`,
  generated_at: generatedAt,
  note: "この artifact はローカル検証対象を列挙する。実 pass/fail は npm run verify と GitHub Actions の実行結果を証跡にする。"
};

write(join(outputRoot, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
console.log(`admin test report artifact generated: ${outputRoot}`);

function suite(name, command) {
  const script = command.replace(/^npm run /, "").replace(/^npm test$/, "test");
  return {
    name,
    command,
    package_script_defined: Boolean(packageJson.scripts[script]),
    ci_workflow_references_command: workflow.includes(command),
    result_source: "local-command-and-ci-workflow"
  };
}

function write(path, body) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
}

function renderReport(items) {
  const rows = items.map((item) => `<tr>
    <td>${escapeHtml(item.name)}</td>
    <td><code>${escapeHtml(item.command)}</code></td>
    <td>${item.package_script_defined ? "defined" : "missing"}</td>
    <td>${item.ci_workflow_references_command ? "referenced" : "not referenced"}</td>
  </tr>`).join("\n");
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Allure compatible local acceptance report</title>
  <style>
    body { font-family: system-ui, sans-serif; line-height: 1.6; margin: 24px; color: #17202a; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #cbd5e1; padding: 8px; text-align: left; }
    th { background: #eef2f7; }
  </style>
</head>
<body>
  <h1>Allure 互換ローカル検証レポート</h1>
  <p>Generated from package scripts and GitHub Actions workflow metadata.</p>
  <table>
    <thead><tr><th>Suite</th><th>Command</th><th>package.json</th><th>CI workflow</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>
</body>
</html>
`;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}
