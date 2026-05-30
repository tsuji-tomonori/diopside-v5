# worker batch v0.4 coverage audit

- 状態: do
- 種別: 設計準拠監査 / contract test
- 対象: `P0-09`, `WORKER-SPLIT`, `BATCH-001〜020`

## 背景

v0.4 設計は BATCH-001〜020 に handler/job_type/queue/test を持つことを検収基準としている。現 main は `static_exporter.pipeline` に複数 worker 責務を統合しており、実装済み batch と未対応 batch の境界を機械的に確認できる状態が不足している。

## 受け入れ条件

- BATCH-001〜020 と現 worker/job_type/queue/test の対応を repo 内文書に整理する。
- 現 pipeline が dispatch できる job_type と queue env mapping を contract test で検証する。
- 未対応または部分実装の batch は、実装済み扱いにせず audit/traceability に明記する。
- `WORKER-SPLIT` と P0-09 の状態を、検証済みの範囲に合わせて更新する。
- `quota_rollup` / `cleanup` など Scheduler job の queue mapping も current contract として固定する。
- `npm test` または同等の最小十分な検証で contract が通ることを確認する。

## 検証予定

- `node tools/check-docs-consistency.mjs`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_worker_batch_coverage_contract.py`
- `git diff --check`
- `npm test`
- `npm run verify`
