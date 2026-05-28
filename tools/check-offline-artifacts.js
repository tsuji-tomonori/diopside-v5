import { createHash } from "node:crypto";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { bm25Documents, bm25GoldenQueries, referenceGraphSamples } from "../packages/testing/src/search-fixtures.js";
import { assert, currentJstTimestamp, isCurrentJstTimestamp, readJson } from "./lib.js";

const outputRoot = "dist/offline-artifacts/local";
rmSync(outputRoot, { recursive: true, force: true });

const artifacts = [
  artifact("raw", "raw_documents", "s3://saphnexa-local/raw/doc-local-1/ver-1/local-1.pdf", { document_count: 5 }),
  artifact("parsed", "parsed_pages", "s3://saphnexa-local/parsed/doc-local-1/ver-1/pages.jsonl", { page_count: 18 }),
  artifact("chunk", "chunk_manifest", "s3://saphnexa-local/chunks/doc-local-1/ver-1/chunks.jsonl", { chunk_count: bm25Documents.length }),
  artifact("reference", "reference_graph", "s3://saphnexa-local/reference-graph/doc-local-1/ver-1/edges.jsonl", { edge_count: referenceGraphSamples.length }),
  artifact("bm25f", "bm25f_index", "s3://saphnexa-local/bm25/doc-local-1/ver-1/postings.jsonl", { query_count: bm25GoldenQueries.length }),
  artifact("parser", "parser_output", "s3://saphnexa-local/parser/doc-local-1/ver-1/result.json", { parser: "local-deterministic-parser" })
];

for (const item of artifacts) {
  write(join(outputRoot, `${item.artifact_id}.json`), `${JSON.stringify(item, null, 2)}\n`);
}

const manifest = {
  schema_version: "offline-artifacts-local.v1",
  generated_by: "tools/check-offline-artifacts.js",
  source_design_version: "v0.16",
  artifacts,
  checksum: `sha256:${sha256(JSON.stringify(artifacts))}`,
  generated_at: currentJstTimestamp(),
  note: "ローカル検収用の offline artifact inventory。実 S3 Vectors / PDF parsing / KB 同期の実行証跡ではない。"
};
write(join(outputRoot, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);

const saved = readJson(join(outputRoot, "manifest.json"));
assert(isCurrentJstTimestamp(saved.generated_at), "offline artifact manifest generated_at must be current JST timestamp");
for (const type of ["raw_documents", "parsed_pages", "chunk_manifest", "reference_graph", "bm25f_index", "parser_output"]) {
  assert(saved.artifacts.some((item) => item.artifact_type === type), `offline artifact missing: ${type}`);
}
for (const item of saved.artifacts) {
  assert(item.s3_uri.startsWith("s3://saphnexa-local/"), `offline artifact URI mismatch: ${item.artifact_id}`);
  assert(/^sha256:[a-f0-9]{64}$/.test(item.checksum), `offline artifact checksum mismatch: ${item.artifact_id}`);
}

console.log("offline artifacts check passed");

function artifact(artifact_id, artifact_type, s3_uri, metadata) {
  const body = JSON.stringify({ artifact_id, artifact_type, s3_uri, metadata });
  return {
    artifact_id,
    artifact_type,
    s3_uri,
    metadata,
    checksum: `sha256:${sha256(body)}`
  };
}

function write(path, body) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, body);
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}
