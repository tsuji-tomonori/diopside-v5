import { existsSync } from "node:fs";
import {
  acceptanceCatalog,
  acceptanceCatalogPath,
  acceptanceIds,
  acceptanceItems,
  allowedTraceStates,
  priorityByAcceptanceId
} from "./acceptance-ids.js";
import { assertSourceChecklistColumns, sourceChecklistColumns } from "./acceptance-checklist-format.js";
import { assert, readText } from "./lib.js";

const expectedPriorityCounts = { P0: 56, P1: 43, P2: 3 };
const expectedItemCount = 102;

assert(acceptanceCatalog.schema_version === "saphnexa-acceptance-source-catalog.v1", "source catalog schema mismatch");
assert(acceptanceCatalog.source_package === "Saphnexa_検収受入条件_package_v1.0", "source package mismatch");
assert(acceptanceCatalog.source_sha256 === "2756d8e28bfad7cefc4b09abaa6e4e0178aee941e7b1eb3c830187af0c84b7ac", "source checklist checksum mismatch");
assert(acceptanceCatalog.source_target_design === "Saphnexa_基本設計書_v0.16.md", "source target design mismatch");
assert(acceptanceCatalog.item_count === expectedItemCount, `source catalog item count must be ${expectedItemCount}`);
assert(acceptanceItems.length === acceptanceCatalog.item_count, "source catalog item_count does not match item rows");
assert(JSON.stringify(acceptanceCatalog.source_columns) === JSON.stringify(sourceChecklistColumns), "source checklist columns mismatch");
assertSourceChecklistColumns(acceptanceCatalog.source_columns, assert);

const ids = new Set();
for (const item of acceptanceItems) {
  assert(/^AC-\d{3}$/.test(item.id), `invalid acceptance id: ${item.id}`);
  assert(!ids.has(item.id), `duplicate acceptance id: ${item.id}`);
  ids.add(item.id);
  for (const key of ["area", "item", "priority", "acceptance_condition", "quantitative_criteria", "evidence", "verification_method"]) {
    assert(String(item[key] || "").length > 0, `${item.id} missing ${key}`);
  }
  assert(["P0", "P1", "P2"].includes(item.priority), `${item.id} invalid priority ${item.priority}`);
}

assert(JSON.stringify(countBy(acceptanceItems, "priority")) === JSON.stringify(expectedPriorityCounts), "priority counts mismatch");
assert(JSON.stringify(acceptanceCatalog.priority_counts) === JSON.stringify(expectedPriorityCounts), "catalog priority_counts mismatch");

const traceRows = parseTraceRows(readText("docs/acceptance/traceability.md"));
const traceById = new Map(traceRows.map((row) => [row.id, row]));
for (const id of acceptanceIds) {
  assert(traceById.has(id), `traceability missing source catalog id ${id}`);
  assert(allowedTraceStates.includes(traceById.get(id).state), `${id} invalid trace state`);
}
for (const row of traceRows) {
  assert(priorityByAcceptanceId[row.id], `traceability has id not present in ${acceptanceCatalogPath}: ${row.id}`);
}
assert(traceRows.length === acceptanceCatalog.item_count, "traceability row count must match source catalog");

if (existsSync("dist/acceptance/acceptance_checklist.draft.csv")) {
  const checklistRows = parseCsv(readText("dist/acceptance/acceptance_checklist.draft.csv"));
  assertSourceChecklistColumns(checklistRows.headers, assert);
  assert(checklistRows.length === acceptanceCatalog.item_count, "draft checklist row count must match source catalog");
  for (const row of checklistRows) {
    const source = acceptanceItems.find((item) => item.id === row.ID);
    assert(source, `draft checklist has id not present in source catalog: ${row.ID}`);
    assert(row["領域"] === source.area, `${row.ID} draft checklist area mismatch`);
    assert(row["重要度"] === source.priority, `${row.ID} draft checklist priority mismatch`);
    assert(row["検収項目"] === source.item, `${row.ID} draft checklist item mismatch`);
    assert(row["受け入れ条件 / 完了条件"] === source.acceptance_condition, `${row.ID} draft checklist condition mismatch`);
  }
}

console.log(`acceptance source catalog check passed (${acceptanceCatalog.item_count} items)`);

function parseTraceRows(body) {
  return [...body.matchAll(/^\| (AC-\d{3}) \| ([a-z_]+) \| (.+) \|$/gm)]
    .map((match) => ({ id: match[1], state: match[2], evidence: match[3] }));
}

function countBy(items, key) {
  return items.reduce((counts, item) => {
    counts[item[key]] = (counts[item[key]] || 0) + 1;
    return counts;
  }, {});
}

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
    if (char === "\"" && quoted && line[index + 1] === "\"") {
      current += "\"";
      index += 1;
    } else if (char === "\"") {
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
