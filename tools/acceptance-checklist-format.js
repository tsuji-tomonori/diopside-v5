export const sourceChecklistColumns = [
  "ID",
  "領域",
  "検収項目",
  "受け入れ条件 / 完了条件",
  "定量基準",
  "監査証跡",
  "確認方法",
  "重要度",
  "結果",
  "証跡リンク",
  "確認者",
  "確認日",
  "備考"
];
export const finalResultColumn = "結果";
export const finalEvidenceColumn = "証跡リンク";
export const finalReviewerColumn = "確認者";
export const finalCheckedDateColumn = "確認日";

export function sourceChecklistValue(row, column) {
  const aliases = {
    結果: ["result"],
    証跡リンク: ["evidence_link"],
    確認者: ["reviewer"],
    確認日: ["checked_date"],
    備考: ["note"],
    領域: ["area"],
    検収項目: ["item"],
    重要度: ["priority"]
  };
  for (const key of [column, ...(aliases[column] || [])]) {
    if (Object.prototype.hasOwnProperty.call(row, key)) return row[key];
  }
  return "";
}

export function assertSourceChecklistColumns(headers, assert) {
  for (const column of sourceChecklistColumns) {
    assert(headers.includes(column), `checklist missing source column: ${column}`);
  }
}
