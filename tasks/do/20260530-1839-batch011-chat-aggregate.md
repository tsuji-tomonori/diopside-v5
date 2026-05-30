# BATCH-011 チャット集計監査

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、BATCH-001〜020 の worker coverage を段階的に精査している。`docs/design/traceability-matrix.md` は BATCH-011 を実装済みとしている一方、`docs/design/worker-batch-coverage-audit.md` は `aggregate worker は未分離` を理由に部分実装のままになっている。

## 目的

BATCH-011 の機能要件である chat summary JSON、時系列ヒート、話者/メッセージ種別統計の生成が現 `chat_normalize` / `ChatAggregateAccumulator` で満たされていることを監査し、物理 worker 分割の残課題とは分けて設計監査ドキュメントへ反映する。

## スコープ

- `docs/design/worker-batch-coverage-audit.md` の BATCH-011 状態と備考。
- `reports/audit/design-v0.4-compliance-20260530.md` の worker coverage 要約。
- 対象テストと docs consistency の検証。
- 作業完了レポート。

## スコープ外

- aggregate 専用 Lambda / queue / job_type の新設。
- chat aggregate payload schema の全面固定。
- 既存 DynamoDB / S3 データの backfill。

## 受け入れ条件

- [x] BATCH-011 の監査表が機能実装済みと物理 worker 分割未対応を区別している。
- [x] compliance audit に BATCH-011 の実装証跡と残課題が追記されている。
- [x] 対象 `tests/test_core_pipeline.py` の chat normalize / aggregate テストが通る。
- [x] docs consistency、diff check、全体 verify が通る。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_pipeline_collect_normalize_and_artifacts tests/test_core_pipeline.py::test_chat_normalize_reads_s3_jsonl_manifest_not_dynamodb_messages tests/test_core_pipeline.py::test_chat_normalize_streams_jsonl_chunks_without_read_jsonl_list tests/test_core_pipeline.py::test_summarize_chat_messages_accepts_single_pass_iterable`
  - 4 passed
- `node tools/check-docs-consistency.mjs`
  - passed
- `git diff --check`
  - passed
- `npm run verify`
  - 136 passed、build、package、local e2e passed

## Done 条件

- 上記受け入れ条件を満たす。
- task md を `tasks/done/` へ移動し、状態を done に更新する。
- 変更を commit / push し、PR に受け入れ条件確認とセルフレビューを日本語コメントする。
