# BATCH-009 replay continuation page 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と v0.4 設計書に沿って、設計準拠差分を継続的に潰す。
- BATCH-009 の replay continuation page 取得を前に進める。

## 要件整理

- BATCH-008 で continuation token は後続 `chat_collect` job へ渡る。
- BATCH-009 では、その token で replay continuation response を取得し、action 正規化、次 continuation 抽出、raw/manifest 保存、後続投入を行う必要がある。
- local test では fake client を使い、YouTube 実 API 呼び出しは発生させない。

## 実施作業

- `apps/shared/src/diopside_core/youtube.py` に `fetch_public_replay_continuation` を追加した。
- `chat_collect` mode=`replay` に `replay_continuation` 分岐を追加し、`replay_client` があればそれを使い、なければ public continuation helper を使うようにした。
- continuation response から action と次 continuation を抽出し、既存 replay flow と同じ raw JSONL / `ChatPageManifest` / next job enqueue に接続した。
- `tests/test_core_pipeline.py` に fake replay client の continuation page test を追加した。
- `docs/design/traceability-matrix.md` と `docs/design/worker-batch-coverage-audit.md` の BATCH-009 を `実装済` に更新した。

## 成果物

- replay continuation token を受けた `chat_collect` が continuation page response を処理できる。
- 次 continuation がある場合、後続 `chat_collect` job を投入できる。
- BATCH-009 は `部分実装` から `実装済` に更新された。

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_replay_continuation_page_fetches_actions_and_requeues_next tests/test_core_pipeline.py::test_public_replay_initial_data_keeps_unknown_renderer_and_continuation`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（136 tests、build、package:deploy、local e2e）

## fit 評価

- BATCH-009 の page collector contract を既存 `chat_collect` / `ChatPageManifest` 境界に沿って実装した。
- worker 物理分割は `WORKER-SPLIT` の差分として引き続き別管理する。

## 未対応・制約・リスク

- 実 YouTube replay continuation response の dev rehearsal は未実施。
- YouTube internal continuation endpoint は public watch HTML と同様に best-effort 扱いで、応答 shape 変更時は parser stats / raw debug を見て追従する必要がある。
