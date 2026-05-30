# batch017 archive finalizer 作業完了レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と v0.4 設計書に沿って、main を v0.4 正本へ寄せる。
- P0-09 / BATCH-001〜020 の不足を段階的に埋める。

## 要件整理

- BATCH-017 のアーカイブ確定処理として、live ended 検知後に replay 取得と static export へつなぐ worker job を追加する。
- 既存の統合 pipeline 前提は維持しつつ、job_type / queue mapping / test / audit を更新する。
- BATCH-017 を未対応扱いのままにせず、実装済み範囲と残差分を明示する。

## 検討・判断

- v0.4 の「遅延実行」は infra/Scheduler まで含むため、本タスクでは `live_status_scan` の archived 遷移検知から aggregate queue に `archive_finalize` を投入する最小経路にした。
- `archive_finalize` は最終 metadata refresh、replay `chat_collect`、`static_export` 投入を行う。
- NotificationPlan 連携や遅延 Scheduler、v0.4 JobMessage 完全移行は後続対象として残した。

## 実施作業

- `archive_finalize` job_type を `static_exporter.pipeline` に追加した。
- `live_status_scan` が `upcoming` / `live` から `archived` へ遷移した動画に対して `archive_finalize` を enqueue するようにした。
- `archive_finalize` が `videos.list` による最終 metadata 更新、replay `chat_collect`、`static_export` を enqueue するようにした。
- queue env mapping、worker batch audit、README、traceability matrix、v0.4 compliance audit、docs consistency contract を更新した。
- `tests/test_core_pipeline.py` と `tests/test_worker_batch_coverage_contract.py` に BATCH-017 の contract を追加した。

## 成果物

- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_core_pipeline.py`
- `tests/test_worker_batch_coverage_contract.py`
- `tools/check-docs-consistency.mjs`
- `README.md`
- `docs/design/worker-batch-coverage-audit.md`
- `docs/design/traceability-matrix.md`
- `reports/audit/design-v0.4-compliance-20260530.md`

## 検証

- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_worker_batch_coverage_contract.py`: 成功、41 tests
- `node tools/check-docs-consistency.mjs`: 成功
- `git diff --check`: 成功
- `npm test`: 成功、86 tests
- `npm run verify`: 成功、test / build / package / local e2e

## fit 評価

- BATCH-017 は未対応から部分実装へ進んだ。
- live ended 検知から replay collect と static export へつながる最小 job chain を追加できた。
- v0.4 の完全な遅延実行・NotificationPlan・JobMessage にはまだ差分が残るため、audit では部分実装として扱った。

## 未対応・制約・リスク

- EventBridge Scheduler による遅延 archive finalizer は未実装。
- NotificationPlan / archive_available 通知連携は未実装。
- `archive_finalize` 後の normalize / aggregate / artifact rebuild は既存手動 job または後続 worker chain に依存する。
