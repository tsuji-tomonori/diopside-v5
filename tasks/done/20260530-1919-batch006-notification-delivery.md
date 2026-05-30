# BATCH-006 notification delivery state

状態: done

タスク種別: 機能追加

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、BATCH-006 配信予定通知生成が通知イベントと任意の外部通知 payload を出力し、`NotificationPlan.delivery_state` を `planned` / `sent` / `skipped` / `failed` で管理することを求めている。現実装は `NotificationPlan` item 作成までで、送信可否や sent/skipped/failed 更新は未対応として監査表に残っている。

## 目的

`notification_plan` が due 済み通知を delivery state へ進められるようにし、外部通知 target がない場合は `skipped`、送信成功時は `sent`、送信失敗時は `failed` を記録する。

## スコープ

- due 判定と delivery state 更新。
- 任意の injected notification client / SNS topic ARN delivery adapter。
- sent/skipped/failed の unit tests。
- BATCH-006 / NotificationPlan の audit docs と README 更新。
- 作業完了レポート。

## スコープ外

- 実 SNS / Discord / Email の疎通確認。
- EventBridge one-shot / SQS delay による due 再投入。
- 物理通知 DLQ の新設。
- public UI への通知 event 表示。

## 計画

1. 現 `notification_plan` と `NotificationPlan` schema を確認する。
2. due 済み plan に対する delivery adapter を追加する。
3. target 未設定、成功、失敗の tests を追加する。
4. docs と report を更新し、targeted checks と `npm run verify` を実行する。
5. PR コメント、task done、push まで完了する。

## ドキュメント保守計画

- `docs/design/worker-batch-coverage-audit.md` と `docs/design/dynamodb-schema-audit.md` の BATCH-006 / NotificationPlan 状態を更新する。
- `reports/audit/design-v0.4-compliance-20260530.md` と README に残課題を明記する。

## 受け入れ条件

- [x] due 未到達の通知は `planned` のまま残る。
- [x] due 済みで target 未設定の通知は `skipped` になる。
- [x] injected notification client が成功した通知は `sent` になり `sent_at` と delivery payload が残る。
- [x] injected notification client が失敗した通知は `failed` になり `last_error_code` が残る。
- [x] BATCH-006 の audit docs が delivery state 実装済みと物理 DLQ / 実外部疎通の残課題を区別している。
- [x] 対象テスト、docs consistency、diff check、全体 verify が通る。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_notification_plan_creates_due_items_idempotently tests/test_core_pipeline.py::test_notification_plan_delivers_due_items_and_records_states tests/test_repository_schema_contract.py::test_repository_accepts_notification_plan_v04_item_shape`
  - 3 passed
- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`
  - passed
- `node tools/check-docs-consistency.mjs`
  - passed
- `git diff --check`
  - passed
- `npm run verify`
  - 140 passed、build、package、local e2e passed

## 検証計画

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_notification_plan_creates_due_items_idempotently tests/test_core_pipeline.py::test_notification_plan_delivers_due_items_and_records_states tests/test_repository_schema_contract.py::test_repository_accepts_notification_plan_v04_item_shape`
- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- 外部通知未設定の初期構成を送信失敗扱いにしていないこと。
- injected client でテスト可能で、実 AWS/SNS 疎通を実施済み扱いしていないこと。
- 既存の future notification plan 作成を壊していないこと。

## リスク

- SNS / Discord / Email の実疎通は未確認。実運用では target 設定と権限、物理 DLQ の確認が別途必要。

## Done 条件

- 実装、テスト、docs 更新、作業レポート作成、PR 本文更新を完了した。
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582533273
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582533428
