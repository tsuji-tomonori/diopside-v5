# batch017 archive finalizer

- 状態: do
- 種別: 機能追加
- 対象: `BATCH-017`, `P0-09`

## 背景

v0.4 設計では BATCH-017 として、live ended 検知から遅延実行し、最終 metadata 再取得、replay 取得、集計/export 投入を行うアーカイブ確定処理が定義されている。現状は `live_status_scan` が `archived` 状態を判定するだけで、後続の replay 取得や static export へつなぐ job がない。

## 受け入れ条件

- `archive_finalize` job_type を worker pipeline に追加する。
- `live_status_scan` が動画を `archived` へ遷移させた場合、`archive_finalize` job を aggregate queue へ投入する。
- `archive_finalize` は対象動画を最終 metadata で更新でき、replay `chat_collect` と `static_export` を enqueue する。
- queue env mapping と worker batch audit は `archive_finalize` を current contract として扱う。
- BATCH-017 の traceability/audit 状態を未対応から部分実装へ更新する。
- unit test と docs consistency が更新済み contract を検証する。

## 検証予定

- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_worker_batch_coverage_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm test`
- `npm run verify`
