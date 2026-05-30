# BATCH-008 replay continuation enqueue

状態: done

## 背景

BATCH-008 は replay 初期化として initial data 解析と continuation 抽出まで実装済みだが、continuation を後続 `chat_collect` job へ渡す contract が不足している。BATCH-009 の実ページ取得は後続としても、初期化 job から page collector へ繋ぐ必要がある。

## 目的

`chat_collect` mode=`replay` が replay continuation を検出した場合に、`DIOPSIDE_CHAT_QUEUE_URL` へ後続 `chat_collect` job を投入し、replay page collector へ繋げる contract を追加する。

## タスク種別

設計準拠実装

## スコープ

- replay continuation 検出時の self enqueue を追加する。
- queue payload に `video_id`、`mode=replay`、continuation token/source/timeout を含める。
- local test で enqueue payload と delay を確認する。
- BATCH-008 の traceability/audit/report を更新する。

## 受け入れ条件

- replay initial data に continuation がある場合、後続 `chat_collect` job が `DIOPSIDE_CHAT_QUEUE_URL` へ投入される。
- continuation token は payload へ保持される。
- local test で YouTube 実 API 呼び出しは発生しない。
- BATCH-009 の実 continuation page fetch は未実装扱いとして残す。
- docs consistency、targeted test、`npm run verify` が pass する。

## 検証計画

- 対象 pytest
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## 完了結果

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_public_replay_initial_data_keeps_unknown_renderer_and_continuation tests/test_core_pipeline.py::test_public_replay_initial_data_extractor`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（135 tests、build、package:deploy、local e2e）
