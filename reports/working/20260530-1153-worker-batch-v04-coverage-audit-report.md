# worker batch v0.4 coverage audit 作業完了レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と v0.4 設計書に沿って、main を v0.4 正本へ寄せる。
- P0-09 の BATCH-001〜020 と worker 実装の差分を、未証明のまま残さない。

## 要件整理

- v0.4 の BATCH-001〜020 に対し、現 worker/job_type/queue/test の対応を repo 内で確認可能にする。
- 未対応または部分実装の batch を実装済み扱いにしない。
- 現 pipeline が dispatch できる job_type と queue env mapping を contract test で固定する。

## 検討・判断

- 現 worker は `static_exporter.pipeline` に metadata/chat/normalize/aggregate/maintenance 責務が統合され、`static_exporter.handler` が static export を担っている。
- BATCH-006 配信予定通知生成、BATCH-017 アーカイブ確定処理、専用 file-output worker、worker 分割責務は未対応または差分として残る。
- `quota_rollup` / `cleanup` は Scheduler 経由で動くが retry 用 queue mapping に未登録だったため、mapping を明示定数化して aggregate queue に固定した。

## 実施作業

- `docs/design/worker-batch-coverage-audit.md` を追加し、BATCH-001〜020 の現対応・queue・test evidence・状態を整理した。
- `tests/test_worker_batch_coverage_contract.py` を追加し、audit coverage、pipeline job_type、queue env mapping、`static_export` の handler 分離を検証した。
- `static_exporter.pipeline` に `PIPELINE_JOB_HANDLERS` と `JOB_QUEUE_ENVS` を追加し、`quota_rollup` / `cleanup` の queue mapping を contract 化した。
- `tools/check-docs-consistency.mjs` に batch audit の必須 batch id / job_type 検査を追加した。
- README、traceability matrix、v0.4 compliance audit を P0-09 の監査済み状態へ更新した。

## 成果物

- `docs/design/worker-batch-coverage-audit.md`
- `tests/test_worker_batch_coverage_contract.py`
- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tools/check-docs-consistency.mjs`
- `README.md`
- `docs/design/traceability-matrix.md`
- `reports/audit/design-v0.4-compliance-20260530.md`

## 検証

- `node tools/check-docs-consistency.mjs`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_worker_batch_coverage_contract.py`: 成功、3 tests
- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`: 成功
- `git diff --check`: 成功
- `npm test`: 成功、85 tests
- `npm run verify`: 成功、test / build / package / local e2e

## fit 評価

- P0-09 は「差分あり」から「監査済み・差分あり」へ進めた。
- v0.4 に対する未対応 batch と統合 worker の差分を、後続実装で参照できる形にした。
- Scheduler / retry の queue mapping を明示したことで、maintenance job の再投入経路が current contract として固定された。

## 未対応・制約・リスク

- BATCH-006、BATCH-017、専用 file-output worker、worker 分割、v0.4 JobMessage 共通 schema への完全移行は未対応。
- `cleanup` は引き続き dry-run report のみで、削除は実行しない。
