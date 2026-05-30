# JobMessage v0.4 schema alignment report

## 指示

- `.workspace/plan-20260530.txt` と `.workspace/` の設計書に沿って v0.4 対応を進める。
- repository の Worktree Task PR Flow に従い、task md、実装、検証、PR 更新、作業レポートを残す。
- 実施していない検証を実施済みとして書かない。

## 要件整理

| 要件ID | 要件 | 対応状況 |
|---|---|---|
| R1 | 管理 API の SQS message を v0.4 `JobMessage` field へ寄せる | 対応 |
| R2 | worker の後続投入 message を v0.4 `JobMessage` field へ寄せる | 対応 |
| R3 | `dispatch_job` が旧 `input` と新 `payload` の両方を処理できる | 対応 |
| R4 | message contract test を追加・更新する | 対応 |
| R5 | README、worker batch audit、traceability を更新する | 対応 |

## 検討・判断

- v0.4 `JobMessage` の required field を shared helper `build_job_message` で組み立て、API と worker の重複実装を避けた。
- 既存外部 producer 互換のため、worker `dispatch_job` は新 `payload` field を優先し、旧 `input` field も fallback として扱う。
- worker 起点の downstream job は親 API request の idempotency key がない場合があるため、`{job_type}:{job_id}` を fallback key にした。
- EventBridge Scheduler template と GitHub Actions workflow_dispatch の message 形状は今回の repository code 変更の外側として、audit の後続課題に残した。

## 実施作業

- `apps/shared/src/diopside_core/repository.py` に `build_job_message` を追加し、public export に含めた。
- 管理 API `_start_job` が queue へ v0.4 `JobMessage` を送るように更新した。
- worker pipeline の metadata pagination、live chat requeue、notification/archive downstream、retry、archive finalize downstream を `JobMessage` へ寄せた。
- `dispatch_job` の新旧 message 互換を追加した。
- API/worker tests と README、worker batch audit、traceability を更新した。

## 成果物

| 成果物 | 内容 |
|---|---|
| `apps/shared/src/diopside_core/repository.py` | `build_job_message` helper |
| `apps/api/src/diopside_api/handler.py` | 管理 API enqueue message の v0.4 化 |
| `apps/workers/static-exporter/src/static_exporter/pipeline.py` | worker downstream message と dispatch 互換 |
| `tests/test_api_handler.py` | 管理 API `JobMessage` contract test |
| `tests/test_core_pipeline.py` | worker downstream と v0.4 payload dispatch tests |
| `README.md` | worker message contract 記述更新 |
| `docs/design/worker-batch-coverage-audit.md` | BATCH-020 と現 worker contract 更新 |
| `docs/design/traceability-matrix.md` | BATCH-020 evidence 更新 |
| `tasks/do/20260530-1647-job-message-v04-schema.md` | 受け入れ条件と検証計画 |

## 実行した検証

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/api/src/diopside_api/handler.py apps/workers/static-exporter/src/static_exporter/pipeline.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py::test_admin_job_enqueue_uses_v04_job_message tests/test_api_handler.py::test_admin_job_dry_run tests/test_api_handler.py::test_admin_remaining_job_apis_dry_run_and_validation`: pass, 3 passed
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_metadata_sync_paginates_saves_raw_and_cursor tests/test_core_pipeline.py::test_live_status_scan_records_quota_and_refreshes_state tests/test_core_pipeline.py::test_live_status_scan_enqueues_notification_plan_for_upcoming_video tests/test_core_pipeline.py::test_live_chat_collect_requeues_with_clamped_delay tests/test_core_pipeline.py::test_worker_pipeline_integration_uses_local_fakes tests/test_core_pipeline.py::test_archive_finalize_refreshes_metadata_and_enqueues_replay_and_export tests/test_core_pipeline.py::test_dispatch_job_accepts_v04_payload_job_message tests/test_core_pipeline.py::test_dispatch_job_supports_scheduled_maintenance_jobs`: pass, 8 passed
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py`: pass, 27 passed
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_worker_batch_coverage_contract.py`: pass, 47 passed
- `npm run verify`: pass, 132 pytest passed + build/package/e2e pass

## 未対応・制約・リスク

- EventBridge Scheduler template と GitHub Actions workflow_dispatch 由来の message 形状統一は未対応。
- 既存外部 producer が旧 `input` 形式で投入する可能性に備え、互換読み取りを残した。

## Fit 評価

総合fit: 4.8 / 5.0

理由: API/worker の SQS message を v0.4 `JobMessage` へ寄せ、互換と検証を維持した。Scheduler/GitHub Actions 側の producer 形状は後続対象として残したため満点ではない。
