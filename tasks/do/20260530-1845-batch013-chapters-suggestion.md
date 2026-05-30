# BATCH-013 chapters_suggestion.md 出力

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、BATCH-013 タイムスタンプ候補生成が `timestamp_candidates.json` と `chapters_suggestion.md` を出力することを求めている。現実装は timestamp JSON と動画 detail への埋め込みに対応しているが、Markdown の章立て候補出力は未実装として worker 監査表に残っている。

## 目的

既存 `build_timestamp_candidates` の結果から、YouTube description へ貼り付けやすい deterministic な `chapters_suggestion.md` を生成し、`rebuild_artifacts` と static export の成果物に接続する。

## スコープ

- timestamp candidate から chapters suggestion Markdown を生成する shared helper。
- `rebuild_artifacts` の processed artifact 出力と `Artifact` item 記録。
- static export の public/versioned chapters suggestion 出力と detail artifacts 参照。
- BATCH-013 の worker audit / compliance audit 更新。
- unit/contract test と作業完了レポート。

## スコープ外

- timestamp 専用 Lambda / queue / job_type の新設。
- 実 YouTube description への書き戻し。
- 既存 S3 / DynamoDB データの backfill。

## 受け入れ条件

- [x] timestamp candidate list から `chapters_suggestion.md` が deterministic に生成される。
- [x] `rebuild_artifacts` が processed bucket に chapters suggestion を出力し、`Artifact` item を記録する。
- [x] static export が alias/versioned chapters suggestion を出力し、detail JSON から参照できる。
- [x] BATCH-013 の監査表が JSON と Markdown 出力の実装状況、物理 worker 分割の残課題を区別している。
- [x] 対象テスト、docs consistency、diff check、全体 verify が通る。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_pipeline_collect_normalize_and_artifacts tests/test_core_pipeline.py::test_generate_chapters_suggestion_markdown_orders_by_offset tests/test_static_exporter.py::test_export_public_data_from_repository`
  - 3 passed
- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py apps/shared/src/diopside_core/__init__.py apps/workers/static-exporter/src/static_exporter/pipeline.py apps/workers/static-exporter/src/static_exporter/handler.py`
  - passed
- `node tools/check-docs-consistency.mjs`
  - passed
- `node tools/check-public-contract.mjs data/fixtures/public`
  - passed
- `git diff --check`
  - passed
- `npm run verify`
  - 初回は test expectation が 60 秒 bucket の仕様とずれて 1 件失敗。期待値を修正後、137 passed、build、package、local e2e passed。

## Done 条件

- 上記受け入れ条件を満たす。
- task md を `tasks/done/` へ移動し、状態を done に更新する。
- 変更を commit / push し、PR に受け入れ条件確認とセルフレビューを日本語コメントする。
