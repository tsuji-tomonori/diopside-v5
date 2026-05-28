import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { dirname, join } from "node:path";
import { currentJstTimestamp, readText } from "./lib.js";

const outputRoot = "dist/admin/docs";
const version = "v0.16";
const generatedAt = currentJstTimestamp();
const sourceFiles = [
  "docs/acceptance/traceability.md",
  "docs/adr/ADR-0001-local-first-acceptance-slice.md",
  "docs/ops/local-verification.md",
  "docs/ops/runbooks/access-change.md",
  "docs/ops/runbooks/backup-restore.md",
  "docs/ops/runbooks/evaluation-rerun.md",
  "docs/ops/runbooks/incident-response.md",
  "docs/ops/runbooks/reingestion.md",
  "docs/ops/runbooks/rollback.md",
  "docs/ops/runbooks/user-import-failure.md"
];

rmSync(outputRoot, { recursive: true, force: true });

const html = renderSite("Saphnexa admin docs", sourceFiles.map((path) => ({
  path,
  body: readText(path)
})));

const latestIndex = join(outputRoot, "latest/index.html");
const versionIndex = join(outputRoot, `versions/${version}/index.html`);
write(latestIndex, html);
write(versionIndex, html);

const manifest = {
  schema_version: "admin-docs-artifact.v1",
  generated_by: "tools/build-admin-docs.js",
  version,
  artifacts: [
    artifact("admin-docs-latest", "/admin/docs/latest/", latestIndex, sourceFiles),
    artifact("admin-docs-version-v0-16", `/admin/docs/versions/${version}/`, versionIndex, sourceFiles)
  ]
};

write(join(outputRoot, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
write(join(outputRoot, "latest/manifest.json"), `${JSON.stringify(manifest.artifacts[0], null, 2)}\n`);
write(join(outputRoot, `versions/${version}/manifest.json`), `${JSON.stringify(manifest.artifacts[1], null, 2)}\n`);

console.log(`admin docs artifact generated: ${outputRoot}`);

function write(path, body) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
}

function artifact(artifact_id, viewer_path, index_path, sources) {
  return {
    artifact_id,
    artifact_type: "design_doc_html",
    title: viewer_path.includes("/versions/") ? "設計書サイト v0.16" : "設計書サイト latest",
    viewer_path,
    index_path,
    status: "published-local",
    source_files: sources,
    checksum: `sha256:${sha256(html)}`,
    generated_at: generatedAt
  };
}

function renderSite(title, documents) {
  const nav = documents.map((doc) => `<li><a href="#${slug(doc.path)}">${escapeHtml(doc.path)}</a></li>`).join("\n");
  const sections = documents.map((doc) => `
    <article id="${slug(doc.path)}">
      <h2>${escapeHtml(doc.path)}</h2>
      ${markdownToHtml(doc.body)}
    </article>`).join("\n");
  return `<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <style>
    body { font-family: system-ui, sans-serif; line-height: 1.65; margin: 0; color: #17202a; background: #f7f9fb; }
    header, main { max-width: 1080px; margin: 0 auto; padding: 24px; }
    header { background: #ffffff; border-bottom: 1px solid #d9e2ec; }
    article { background: #ffffff; border: 1px solid #d9e2ec; border-radius: 6px; padding: 20px; margin: 16px 0; }
    pre { overflow: auto; background: #f1f5f9; padding: 12px; border-radius: 6px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; vertical-align: top; }
  </style>
</head>
<body>
  <header>
    <h1>${escapeHtml(title)}</h1>
    <p>Local acceptance artifact for admin-only publication checks.</p>
    <nav><ul>${nav}</ul></nav>
  </header>
  <main>${sections}</main>
</body>
</html>
`;
}

function markdownToHtml(markdown) {
  const lines = markdown.split("\n");
  const out = [];
  let inList = false;
  let inPre = false;
  for (const line of lines) {
    if (line.startsWith("```")) {
      out.push(inPre ? "</pre>" : "<pre>");
      inPre = !inPre;
      continue;
    }
    if (inPre) {
      out.push(escapeHtml(line));
      continue;
    }
    if (line.startsWith("# ")) out.push(`<h1>${escapeHtml(line.slice(2))}</h1>`);
    else if (line.startsWith("## ")) out.push(`<h2>${escapeHtml(line.slice(3))}</h2>`);
    else if (line.startsWith("### ")) out.push(`<h3>${escapeHtml(line.slice(4))}</h3>`);
    else if (line.startsWith("- ")) {
      if (!inList) out.push("<ul>");
      inList = true;
      out.push(`<li>${escapeHtml(line.slice(2))}</li>`);
    } else {
      if (inList) out.push("</ul>");
      inList = false;
      out.push(line.trim() ? `<p>${escapeHtml(line)}</p>` : "");
    }
  }
  if (inList) out.push("</ul>");
  if (inPre) out.push("</pre>");
  return out.join("\n");
}

function slug(value) {
  return value.replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-|-$/g, "");
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
