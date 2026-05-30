# BATCH-008 replay continuation enqueue 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と v0.4 設計書に沿って、設計準拠差分を継続的に潰す。
- replay chat collect 周辺の部分実装を前に進める。

## 要件整理

- replay 初期化は initial data / HTML から replay action と continuation を抽出し、後続 page collect に繋げる必要がある。
- 現状は continuation を `next_poll` に残すだけで、後続 `chat_collect` job へ投入していなかった。
- continuation token から実ページを取得する BATCH-009 は別途残す。

## 実施作業

- `chat_collect` mode=`replay` で continuation が見つかった場合、`DIOPSIDE_CHAT_QUEUE_URL` へ後続 `chat_collect` job を投入するようにした。
- 後続 payload には `video_id`、`mode=replay`、`replay_continuation` の token/source/timeout を含めるようにした。
- continuation の `timeout_ms` から delay seconds を設定するようにした。
- `tests/test_core_pipeline.py` の replay initial data test で queue env、payload、delay を検証した。
- `docs/design/traceability-matrix.md` と `docs/design/worker-batch-coverage-audit.md` の BATCH-008 を `実装済` に更新した。

## 成果物

- replay initial data 解析後に continuation がある場合、後続 `chat_collect` job へ繋がる。
- BATCH-008 は `部分実装` から `実装済` に更新された。
- BATCH-009 は continuation token からの実ページ取得が未実装のため `部分実装` のまま残した。

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_public_replay_initial_data_keeps_unknown_renderer_and_continuation tests/test_core_pipeline.py::test_public_replay_initial_data_extractor`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（135 tests、build、package:deploy、local e2e）

## fit 評価

- BATCH-008 の初期化責務である continuation 抽出と後続投入 contract を実装した。
- BATCH-009 の実ページ取得は実装済み扱いにせず、後続課題として残した。

## 未対応・制約・リスク

- continuation token からの実 replay page 取得は未対応。
- 実 YouTube replay continuation の dev rehearsal は未実施。
