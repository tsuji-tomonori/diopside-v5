# 管理 UI quota summary 表示

状態: done

タスク種別: 機能追加

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、管理者が quota 使用量と上限接近状況を確認できることが求められている。API-020 は `items` に加えて `daily`、`by_method`、`limit_per_day`、`warning` を返すようになったが、管理 UI は call record `items` のみを表示している。

## 目的

管理 UI の quota panel で daily summary、method summary、warning を表示し、既存 call record 表示も維持する。

## スコープ

- `apps/web/public/app.js` の quota render 更新。
- local e2e / DOM safety / API response 互換の確認。
- README / audit report の残課題更新。
- 作業完了レポート。

## スコープ外

- API-020 の schema 追加変更。
- CloudWatch Alarm / 外部通知 delivery。
- 既存 data backfill。

## 計画

1. 現 quota panel の DOM 構造を確認する。
2. `renderQuotaUsage` を response 全体を受け取る形にし、warning / daily / by_method / call records を表示する。
3. local e2e で quota summary 表示を検証する。
4. docs / report を更新し、`npm run verify` まで実行する。

## ドキュメント保守計画

- README の管理 UI / quota 表示説明を更新する。
- `reports/audit/design-v0.4-compliance-20260530.md` の API-020 / quota rollup 残課題を更新する。

## 受け入れ条件

- [x] 管理 UI の quota panel が `warning` を表示できる。
- [x] 管理 UI の quota panel が `daily` と `by_method` summary を表示できる。
- [x] 既存 call record `items` 表示を維持している。
- [x] local e2e で quota 表示を確認している。
- [x] 対象チェック、diff check、全体 verify が通る。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `node --check apps/web/public/app.js`
  - passed
- `python3 -m py_compile apps/api/src/diopside_api/local_server.py`
  - passed
- `node tools/check-web-dom-safety.mjs`
  - passed
- `npm run e2e:local`
  - passed
- `node tools/check-docs-consistency.mjs`
  - passed
- `git diff --check`
  - passed
- `npm run verify`
  - 139 passed、build、package、local e2e passed

## 検証計画

- `node --check apps/web/public/app.js`
- `node tools/check-web-dom-safety.mjs`
- `npm run e2e:local`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- UI が API の optional field 欠落時も壊れないこと。
- call record 表示が残っていること。
- 未実施の外部通知 / Alarm / backfill を実施済み扱いしていないこと。

## Done 条件

- [x] 上記受け入れ条件を満たす。
- [x] task md を `tasks/done/` へ移動し、状態を done に更新する。
- [x] 変更を commit / push し、PR に受け入れ条件確認とセルフレビューを日本語コメントする。

## PR コメント

- 受け入れ条件確認: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582516662
- セルフレビュー: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582517298

## リスク

- 既存環境で daily summary が未作成の場合、summary は空表示になる。これは API 互換上の想定挙動で、backfill は後続対象。
