# BATCH-016 quota threshold warning event 作業完了レポート

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-05-30 |
| 対象 | `.workspace/plan-20260530.txt` v0.4 設計準拠対応 |
| task | `tasks/do/20260530-1856-batch016-quota-warning.md` |

## 受けた指示

`.workspace/plan-20260530.txt` と `.workspace/` 配下の設計書に基づき、`main` を pull した上で v0.4 設計準拠対応を進める。

## 要件整理

- BATCH-016 は日別・method別 quota summary と警告イベントを出力する。
- v0.4 の `QuotaUsage` daily summary は `warning_emitted` を必須属性としている。
- 外部通知 delivery、管理 UI daily summary 表示、CloudWatch Alarm は別差分として扱う。

## 検討・判断

既存 `quota_rollup` は call record から daily method summary を保存していたが、warning 状態を持っていなかった。今回は日次合計が `warning_threshold_units` 以上の場合に summary item へ `warning_emitted=true` と warning metadata を保存し、同じ summary で未通知の場合だけ `quota_threshold_warning` JobEvent を記録する形にした。

既定閾値は 9000 units とした。これは YouTube API の一般的な日次 10,000 units に対する 90% 近似であり、運用では job payload の `warning_threshold_units` で上書きできる。

## 実施作業

- `quota_rollup` に `warning_threshold_units`、`warning_emitted`、`warning_total_units` を追加した。
- 閾値超過時に `quota_threshold_warning` JobEvent を 1 回だけ記録するようにした。
- 閾値未満では warning event が出ないこと、再実行で重複 warning event が出ないことを test で固定した。
- BATCH-016 の traceability、worker audit、DDB audit、README、compliance audit を更新した。

## 成果物

- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_core_pipeline.py`
- `tests/test_repository_schema_contract.py`
- `docs/design/traceability-matrix.md`
- `docs/design/worker-batch-coverage-audit.md`
- `docs/design/dynamodb-schema-audit.md`
- `reports/audit/design-v0.4-compliance-20260530.md`
- `README.md`
- `tasks/do/20260530-1856-batch016-quota-warning.md`
- `reports/working/20260530-1856-batch016-quota-warning.md`

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

## fit 評価

- BATCH-016 の warning event と `warning_emitted` summary metadata を実装し、v0.4 の主要未対応を解消した。
- 外部通知 delivery / 管理 UI daily summary 表示 / CloudWatch Alarm は実施していないため、これらは後続差分として docs と report に明記した。
- `.workspace/plan-20260530.txt` 全体の残課題は継続中であり、本レポートは BATCH-016 warning event のみを完了対象とする。

## 未対応・制約・リスク

- 外部通知 delivery は未実装。
- 管理 UI で daily summary / warning を表示する拡張は未対応。
- CloudWatch Alarm / CDK 連携は未対応。
- 既存 DynamoDB data への backfill は未実施。
- dev 環境、CloudFront、実 YouTube データでの rehearsal は未実施。
