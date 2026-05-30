# BATCH-009 replay continuation page

状態: done

## 背景

BATCH-008 で replay initial data から continuation を抽出し、後続 `chat_collect` job へ投入する contract は追加済み。BATCH-009 は continuation token を使って replay page を取得し、次 continuation を処理する経路が不足している。

## 目的

`chat_collect` mode=`replay` が `replay_continuation` を受け取ったとき、continuation page response を取得・解析し、message と次 continuation を保存・再投入できるようにする。

## タスク種別

設計準拠実装

## スコープ

- YouTube replay continuation response から replay action / continuation を抽出する helper を追加する。
- `chat_collect` に `replay_continuation` 分岐を追加する。
- local test では fake client / fixture response を使い、YouTube 実 API 呼び出しを発生させない。
- BATCH-009 の traceability/audit/report を更新する。

## 受け入れ条件

- `replay_continuation` payload の token が continuation page fetch に渡る。
- continuation response の actions が normalized raw JSONL と `ChatPageManifest` に保存される。
- 次 continuation がある場合は後続 `chat_collect` job が投入される。
- BATCH-009 が `部分実装` のまま放置されない。
- docs consistency、targeted test、`npm run verify` が pass する。

## 検証計画

- 対象 pytest
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## 完了結果

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_replay_continuation_page_fetches_actions_and_requeues_next tests/test_core_pipeline.py::test_public_replay_initial_data_keeps_unknown_renderer_and_continuation`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（136 tests、build、package:deploy、local e2e）
