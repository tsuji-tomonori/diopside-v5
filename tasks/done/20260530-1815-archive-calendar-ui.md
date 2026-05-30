# Archive calendar UI

状態: done

## 背景

v0.4 の P1 差分として Archive calendar は `/data/calendar/{year}.json` と `GET /api/archive-calendar` が実装済みだが、公開 UI から年/月別アーカイブへ辿る導線が未対応として audit に残っている。

## 目的

公開 UI で archive calendar を読み込み、月別 chip から該当年月の動画一覧へ絞り込めるようにする。

## タスク種別

機能追加

## スコープ

- static manifest の `STATIC-005` から calendar JSON を読み込む。
- 公開 UI に archive calendar section を追加し、年/月別 chip を表示する。
- month filter を state と filter sheet に追加する。
- calendar chip click で year/month filter を適用し、動画一覧を絞り込む。
- local e2e で archive calendar 表示と月別絞り込みを確認する。
- README、traceability、audit、作業レポートを更新する。

## 計画

1. existing public data manifest と calendar JSON shape を確認する。
2. UI state/filter に month を追加する。
3. archive calendar section と render logic を追加する。
4. local e2e と docs を更新する。
5. 対象検証と `npm run verify` を実行する。

## ドキュメント保守方針

README の public UI/API 説明、`docs/design/traceability-matrix.md`、audit report の Archive calendar 差分を更新する。設計書正本は変更しない。

## 受け入れ条件

- public UI が `/data/calendar/{year}.json` を manifest 経由で読み込める。
- archive calendar section に year/month と video count が表示される。
- month chip click で year/month filter が適用され、動画一覧が該当年月へ絞り込まれる。
- filter sheet でも month filter を確認・変更できる。
- calendar data がない場合は empty state を表示し、架空 calendar を表示しない。
- local e2e が archive calendar 表示と月別絞り込みを検証する。
- README、traceability、audit が更新済みである。
- 選定した検証コマンドが pass し、未実施検証があれば理由を記録する。

## 検証計画

- `node --check apps/web/public/app.js`
- `node tools/check-web-dom-safety.mjs`
- `node tools/check-docs-consistency.mjs`
- `npm run e2e:local`
- `git diff --check`
- `npm run verify`

## 完了結果

- `node --check apps/web/public/app.js`: pass
- `node tools/check-web-dom-safety.mjs`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `npm run e2e:local`: pass
- `git diff --check`: pass
- `npm run verify`: pass（135 tests、build、package:deploy、local e2e）

## PR レビュー観点

- calendar は manifest/static data 由来だけを表示し、固定 fallback を追加していないこと。
- month filter が既存 tag/search/year/duration filters を壊していないこと。
- mobile bottom sheet で text overflow や操作不能が起きないこと。
