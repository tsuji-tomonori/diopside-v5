# BATCH-016 quota threshold warning event

状態: done

タスク種別: 機能追加

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、BATCH-016 quota 使用量ロールアップが「日別・method別 quota summary、警告イベント」を出力することを求めている。現実装は call record から daily method summary を保存するが、`warning_emitted` と閾値超過時の警告イベントは未実装として監査表に残っている。

## 目的

`quota_rollup` が日別・method別 summary に warning 状態を保存し、日次合計が閾値を超えた場合に job event として quota threshold warning を記録する。

## スコープ

- `quota_rollup` の warning threshold 判定。
- `QuotaUsage` daily summary の `warning_emitted` / `warning_threshold_units` / `warning_total_units` 保存。
- 閾値超過時の `JobEvent` 記録。
- BATCH-016 の traceability / worker audit / DDB audit / README / compliance audit 更新。
- unit tests と作業完了レポート。

## スコープ外

- 外部通知 delivery。
- 管理 UI の quota summary 表示拡張。
- CloudWatch Alarm / CDK 連携。
- 既存 DynamoDB データの backfill。

## 計画

1. 現 `quota_rollup` と v0.4 の QuotaUsage schema を確認する。
2. `quota_rollup` に `warning_threshold_units` を追加し、未指定時は 9000 units を既定値にする。
3. 閾値超過時に `quota_threshold_warning` JobEvent を append し、summary item へ warning metadata を保存する。
4. targeted tests と docs を更新する。
5. `npm run verify` まで実行し、PR コメントへ受け入れ条件確認とセルフレビューを残す。

## ドキュメント保守計画

- `docs/design/traceability-matrix.md` と `docs/design/worker-batch-coverage-audit.md` の BATCH-016 状態を更新する。
- `docs/design/dynamodb-schema-audit.md` と `reports/audit/design-v0.4-compliance-20260530.md` の quota warning 記述を更新する。
- `README.md` の quota 節約方針を実装に合わせる。

## 受け入れ条件

- [x] `quota_rollup` が daily method summary に `warning_emitted` を保存する。
- [x] 閾値超過時に `quota_threshold_warning` JobEvent が記録される。
- [x] 閾値未満では warning event が出ない。
- [x] BATCH-016 の監査 docs が warning event 実装済みと外部通知 / UI / Alarm の残課題を区別している。
- [x] 対象テスト、docs consistency、diff check、全体 verify が通る。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_quota_rollup_summarizes_usage_and_stores_daily_method_items tests/test_core_pipeline.py::test_quota_rollup_emits_threshold_warning_event_once tests/test_core_pipeline.py::test_dispatch_job_supports_scheduled_maintenance_jobs`
  - 3 passed
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py::test_repository_keeps_quota_daily_summary_out_of_call_record_list`
  - 1 passed
- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`
  - passed
- `node tools/check-docs-consistency.mjs`
  - passed
- `git diff --check`
  - passed
- `npm run verify`
  - 138 passed、build、package、local e2e passed

## 検証計画

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_quota_rollup_summarizes_usage_and_stores_daily_method_items tests/test_core_pipeline.py::test_quota_rollup_emits_threshold_warning_event tests/test_core_pipeline.py::test_dispatch_quota_rollup_job`
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py::test_repository_keeps_quota_daily_summary_out_of_call_record_list`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- warning threshold がテスト専用値ではなく job payload で上書き可能な運用値になっていること。
- warning event が同一 rollup の検収証跡として残り、未実施の外部通知を実施済み扱いしていないこと。
- call record と daily summary の list 互換を壊していないこと。

## Done 条件

- [x] 上記受け入れ条件を満たす。
- [x] task md を `tasks/done/` へ移動し、状態を done に更新する。
- [x] 変更を commit / push し、PR に受け入れ条件確認とセルフレビューを日本語コメントする。

## PR コメント

- 受け入れ条件確認: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582481893
- セルフレビュー: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582483757

## リスク

- 既定閾値 9000 units は v0.4 に明記された数値ではなく、YouTube API の一般的な日次 quota 10,000 units に対する 90% 近似である。設定化は後続対象。
- 外部通知 delivery / CloudWatch Alarm までは今回含めない。
