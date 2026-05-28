import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { acceptanceIds, acceptanceItemById } from "./acceptance-ids.js";
import { sourceChecklistColumns } from "./acceptance-checklist-format.js";
import { buildFinalAcceptanceChecklistFromFile, buildFinalAcceptanceChecklistRows } from "./final-acceptance-checklist.js";
import { assert, readText } from "./lib.js";

const root = mkdtempSync(join(tmpdir(), "saphnexa-final-checklist-"));

try {
  const inputPath = join(root, "checklist-signoff.uat.json");
  const outputPath = join(root, "acceptance_checklist.csv");
  writeFileSync(inputPath, `${JSON.stringify(signoffFixture(), null, 2)}\n`);

  const rows = buildFinalAcceptanceChecklistFromFile({ inputPath, outputPath });
  const csvRows = parseCsv(readText(outputPath));
  assert(rows.length === acceptanceIds.length, "final checklist rows must match acceptance ids");
  assert(JSON.stringify(csvRows.headers) === JSON.stringify(sourceChecklistColumns), "final checklist columns must match source columns");
  assert(JSON.stringify(rows.map((row) => row.ID)) === JSON.stringify(acceptanceIds), "final checklist rows must preserve source order");
  assert(JSON.stringify(csvRows.map((row) => row.ID)) === JSON.stringify(acceptanceIds), "written checklist rows must preserve source order");

  for (const row of rows) {
    const source = acceptanceItemById[row.ID];
    assert(row.結果 === "PASS", `${row.ID} result must be PASS`);
    assert(row.領域 === source.area, `${row.ID} area mismatch`);
    assert(row.重要度 === source.priority, `${row.ID} priority mismatch`);
    assert(row.検収項目 === source.item, `${row.ID} item mismatch`);
    assert(row["受け入れ条件 / 完了条件"] === source.acceptance_condition, `${row.ID} condition mismatch`);
    assert(row.証跡リンク.startsWith("https://github.com/tsuji-tomonori/saphnexa/"), `${row.ID} evidence url mismatch`);
    assert(row.確認者 === "acceptance-reviewer", `${row.ID} reviewer mismatch`);
    assert(row.確認日 === "2026-05-27", `${row.ID} checked date mismatch`);
    assert(row.備考 === "final acceptance signed evidence", `${row.ID} note mismatch`);
  }
  assert(rows.find((row) => row.ID === acceptanceIds[0]).証跡リンク.endsWith("/actions/runs/26494798563"), "override evidence url must be applied");

  assertThrows(() => buildFinalAcceptanceChecklistRows({ ...signoffFixture(), default_evidence_url: "" }), "signoff.default_evidence_url must be populated");
  assertThrows(() => buildFinalAcceptanceChecklistRows({ ...signoffFixture(), checked_date: "2026-02-30" }), "signoff.checked_date must be a real calendar date");
  assertThrows(
    () =>
      buildFinalAcceptanceChecklistRows({
        ...signoffFixture(),
        overrides: {
          "AC-999": {
            evidence_url: "https://github.com/tsuji-tomonori/saphnexa/actions/runs/26494798563"
          }
        }
      }),
    "unknown acceptance id"
  );

  console.log("final acceptance checklist fixture check passed");
} finally {
  rmSync(root, { recursive: true, force: true });
}

function signoffFixture() {
  return {
    default_evidence_url: "https://github.com/tsuji-tomonori/saphnexa/pull/1",
    reviewer: "acceptance-reviewer",
    checked_date: "2026-05-27",
    note: "final acceptance signed evidence",
    overrides: {
      [acceptanceIds[0]]: {
        evidence_url: "https://github.com/tsuji-tomonori/saphnexa/actions/runs/26494798563"
      }
    }
  };
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

function assertThrows(fn, message) {
  try {
    fn();
  } catch (error) {
    assert(error.message.includes(message), `unexpected error: ${error.message}`);
    return;
  }
  throw new Error(`expected error: ${message}`);
}
