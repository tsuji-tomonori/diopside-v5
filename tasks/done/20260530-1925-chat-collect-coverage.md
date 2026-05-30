# BATCH-007-009 chat collect coverage

状態: done

## 背景

`BATCH-007` 公式 Live Chat 取得、`BATCH-008` リプレイチャット初期化、`BATCH-009` リプレイチャットページ取得が `部分実装` のまま残っている。現 `chat_collect` の実装とテスト証跡を確認し、不足している取得経路を前に進める。

## 目的

live/replay chat collect の実装・検証状況を明確化し、少なくとも 1 項目を v0.4 準拠へ近づける。

## タスク種別

設計準拠監査・実装

## スコープ

- `chat_collect` の live/replay mode と continuation handling を確認する。
- 不足時は最小実装とテストを追加する。
- traceability、audit、作業レポートを更新する。

## 受け入れ条件

- BATCH-007〜009 の少なくとも 1 つが現状より明確に前進する。
- 実装ファイルとテストが traceability に明記される。
- YouTube 実 API 呼び出しは local test で発生しない。
- docs consistency、targeted test、`npm run verify` が pass する。

## 検証計画

- 対象 pytest
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## 完了結果

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_live_chat_collect_requeues_with_clamped_delay tests/test_core_pipeline.py::test_live_chat_collect_records_quota_when_calling_youtube tests/test_core_pipeline.py::test_live_chat_collect_stops_when_offline tests/test_core_pipeline.py::test_live_chat_collect_does_not_requeue_on_rate_limit`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（135 tests、build、package:deploy、local e2e）
