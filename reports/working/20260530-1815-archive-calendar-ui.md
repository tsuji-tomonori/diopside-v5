# 月別アーカイブ UI 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と `.workspace/` 配下の設計書に沿って、main を pull した上で v0.4 準拠差分を進める。
- Worktree Task PR Flow に従い、task md、実装、検証、PR 更新まで行う。

## 要件整理

- 既存の `/data/calendar/{year}.json` と `GET /api/archive-calendar` に対して、公開 UI から月別アーカイブを辿れる導線を追加する。
- calendar 表示は manifest の STATIC-005 由来に限定し、架空の fallback 月を表示しない。
- month chip 選択時に year/month filter を適用し、filter sheet と同期する。
- local e2e で表示と選択状態を検証する。

## 実施作業

- `apps/web/public/index.html` に月別アーカイブ section と filter sheet の month select を追加した。
- `apps/web/public/app.js` に `calendarMonths` と `month` state、STATIC-005 読み込み、archive chip 描画、year/month 絞り込みを追加した。
- `apps/web/public/styles.css` に既存 chip UI と同じ archive section/chip のスタイルを追加した。
- `tools/run-local-e2e.mjs` に `2026/05 2件` の表示と chip 選択状態の検証を追加した。
- `README.md`、`docs/design/traceability-matrix.md`、`reports/audit/design-v0.4-compliance-20260530.md` を更新し、公開 UI 側の Archive calendar 対応を反映した。

## 成果物

- 公開 UI で STATIC-005 の calendar JSON から月別 chip を表示できる。
- 月別 chip 選択で検索語と tag をクリアし、year/month filter を動画一覧と filter sheet に同期する。
- calendar data がない場合は empty state を表示する。

## 検証

- `node --check apps/web/public/app.js`: pass
- `node tools/check-web-dom-safety.mjs`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run e2e:local`: pass
- `npm run verify`: pass（135 tests、build、package:deploy、local e2e）

## fit 評価

- 受け入れ条件のうち UI 表示、month chip 適用、filter sheet 同期、empty state、local e2e、関連 docs 更新は対応済み。
- v0.4 の Next.js static export 化、既存 `VideoMonthIndex` backfill、実 dev 環境での YouTube 実データ E2E はこの小タスクの範囲外として継続課題に残る。

## 未対応・制約・リスク

- month select は月のみの選択であり、年指定が空の場合は同じ月の全年度を対象にする。年月単位の明示選択は archive chip で行う。
- 実 dev 環境、CloudFront、YouTube 実データでの確認は未実施。
