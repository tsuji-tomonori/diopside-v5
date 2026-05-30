# batch006 notification plan

- 状態: do
- 種別: 機能追加
- 対象: `BATCH-006`, `NotificationPlan`, `P0-09`

## 背景

v0.4 設計では BATCH-006 として、配信30分前・開始時刻・archive_available などの通知予定を `NotificationPlan` item として扱う。現状は live 状態監視や archive finalizer はあるが、通知予定 item と通知計画 job が未実装で、BATCH-006 と DDB `NotificationPlan` が未対応のまま残っている。

## 受け入れ条件

- `NotificationPlan` item_type を repository current contract に追加する。
- `notification_plan` job_type を worker pipeline に追加する。
- `notification_plan` は `before_30min`、`at_start`、`archive_available` の `NotificationPlan` item を冪等に作成・更新できる。
- `live_status_scan` は upcoming 動画の `scheduled_start_time` から `notification_plan` を enqueue する。
- `archive_finalize` は `archive_available` の `NotificationPlan` を作成できる。
- DDB schema audit、worker batch audit、traceability、README、docs consistency を更新する。
- unit test と docs consistency が更新済み contract を検証する。

## 検証予定

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_repository_schema_contract.py tests/test_worker_batch_coverage_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm test`
- `npm run verify`
