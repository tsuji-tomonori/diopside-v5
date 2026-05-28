import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { acceptanceIds, acceptanceItemById } from "./acceptance-ids.js";
import { sourceChecklistColumns } from "./acceptance-checklist-format.js";
import { readJson } from "./lib.js";

export const finalChecklistPath = "docs/acceptance/final/acceptance_checklist.csv";
export const finalChecklistSignoffInputPath = "docs/acceptance/final/checklist-signoff.uat.json";

export function buildFinalAcceptanceChecklistFromFile(options = {}) {
  const inputPath = options.inputPath || finalChecklistSignoffInputPath;
  const outputPath = options.outputPath || finalChecklistPath;
  const signoff = readJson(inputPath);
  const rows = buildFinalAcceptanceChecklistRows(signoff);
  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, renderFinalAcceptanceChecklistCsv(rows));
  return rows;
}

export function buildFinalAcceptanceChecklistRows(signoff) {
  validateSignoff(signoff);
  const overrides = signoff.overrides || {};
  return acceptanceIds.map((id) => {
    const source = acceptanceItemById[id];
    const override = overrides[id] || {};
    const evidenceUrl = override.evidence_url || signoff.default_evidence_url;
    const reviewer = override.reviewer || signoff.reviewer;
    const checkedDate = override.checked_date || signoff.checked_date;
    const note = override.note || signoff.note || "final acceptance signoff";
    assertFinalText(evidenceUrl, `signoff.${id}.evidence_url`);
    assertFinalText(reviewer, `signoff.${id}.reviewer`);
    assertIsoDate(checkedDate, `signoff.${id}.checked_date`);
    assertFinalText(note, `signoff.${id}.note`);
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
      証跡リンク: evidenceUrl,
      確認者: reviewer,
      確認日: checkedDate,
      備考: note
    };
  });
}

export function renderFinalAcceptanceChecklistCsv(rows) {
  return `${sourceChecklistColumns.join(",")}\n${rows.map((row) => sourceChecklistColumns.map((key) => csv(row[key])).join(",")).join("\n")}\n`;
}

function validateSignoff(signoff) {
  assert(signoff && typeof signoff === "object" && !Array.isArray(signoff), "signoff input must be an object");
  assertFinalText(signoff.default_evidence_url, "signoff.default_evidence_url");
  assertFinalText(signoff.reviewer, "signoff.reviewer");
  assertIsoDate(signoff.checked_date, "signoff.checked_date");
  if (signoff.note !== undefined) assertFinalText(signoff.note, "signoff.note");
  const overrides = signoff.overrides || {};
  assert(overrides && typeof overrides === "object" && !Array.isArray(overrides), "signoff.overrides must be an object");
  for (const id of Object.keys(overrides)) {
    assert(acceptanceItemById[id], `signoff.overrides contains unknown acceptance id: ${id}`);
  }
}

function assertFinalText(value, label) {
  assert(typeof value === "string" && value.trim().length > 0, `${label} must be populated`);
  assert(!/pending|example|draft|placeholder|not-for-acceptance/i.test(value), `${label} must be final text`);
}

function assertIsoDate(value, label) {
  assert(typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value), `${label} must be YYYY-MM-DD`);
  const date = new Date(`${value}T00:00:00.000Z`);
  assert(!Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value, `${label} must be a real calendar date`);
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function csv(value) {
  const text = String(value ?? "");
  if (!/[",\n]/.test(text)) return text;
  return `"${text.replaceAll('"', '""')}"`;
}
