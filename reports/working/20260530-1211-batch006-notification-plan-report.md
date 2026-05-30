# batch006 notification plan 作業完了レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と v0.4 設計書に沿って、main を v0.4 正本へ寄せる。
- P0-09 / BATCH-001〜020 の不足を段階的に埋める。

## 要件整理

- BATCH-006 の配信予定通知生成として、`before_30min`、`at_start`、`archive_available` の `NotificationPlan` item を扱えるようにする。
- 現 worker pipeline に `notification_plan` job_type を追加し、live status scan / archive finalizer から通知計画へつなぐ。
- 外部通知 delivery は v0.4 の optional 連携を含むため、本タスクでは item 作成までを部分実装として扱う。

## 検討・判断

- `NotificationPlan` は v0.4 の key shape `VID#{video_id}` / `NOTIFY#{notification_type}` と `gsi3pk=NOTIFY#DUE` を採用した。
- 既存の `VIDEO#` key を使う `Video` item との互換は維持し、通知予定 item だけ v0.4 に寄せた。
- 外部通知 delivery、通知 DLQ、`sent` / `skipped` / `failed` 更新は後続タスクとして残した。

## 実施作業

- repository の `ITEM_TYPES` に `NotificationPlan` を追加した。
- `static_exporter.pipeline` に `notification_plan` job_type と aggregate queue mapping を追加した。
- `notification_plan` が `before_30min`、`at_start`、`archive_available` を冪等に作成・更新するようにした。
- `live_status_scan` が upcoming 動画の `scheduled_start_time` から `notification_plan` を enqueue するようにした。
- `archive_finalize` が `archive_available` の `NotificationPlan` を作成するようにした。
- README、DDB schema audit、worker batch audit、traceability matrix、v0.4 compliance audit、docs consistency contract を更新した。
- `tests/test_core_pipeline.py`、`tests/test_repository_schema_contract.py`、`tests/test_worker_batch_coverage_contract.py` に contract を追加した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_core_pipeline.py`
- `tests/test_repository_schema_contract.py`
- `tests/test_worker_batch_coverage_contract.py`
- `tools/check-docs-consistency.mjs`
- `README.md`
- `docs/design/dynamodb-schema-audit.md`
- `docs/design/worker-batch-coverage-audit.md`
- `docs/design/traceability-matrix.md`
- `reports/audit/design-v0.4-compliance-20260530.md`

## 検証

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_repository_schema_contract.py tests/test_worker_batch_coverage_contract.py`: 成功、48 tests
- `node tools/check-docs-consistency.mjs`: 成功
- `git diff --check`: 成功
- `npm test`: 成功、89 tests
- `npm run verify`: 成功、test / build / package / local e2e

## fit 評価

- BATCH-006 は未対応から部分実装へ進んだ。
- v0.4 の `NotificationPlan` item shape と due index を repository / worker contract に入れた。
- `live_status_scan` と `archive_finalize` から通知計画が作られるため、配信予定・開始・archive_available 候補の保存要件を満たす方向へ前進した。

## 未対応・制約・リスク

- 外部通知 delivery、通知 DLQ、`sent` / `skipped` / `failed` 更新は未実装。
- EventBridge Scheduler で due notification を dispatch する処理は未実装。
- 通知文テンプレートや送信 target は `none` / notification_type を既定値として保存するのみ。
