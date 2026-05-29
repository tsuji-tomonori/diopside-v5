# DynamoDB repository と Job lifecycle の実データ経路強化

状態: do
タスク種別: 機能追加

## 背景

`.workspace/plan-20260529.txt` の Phase 1 は、本番データ pipeline 完成に向けて P1-01 から P1-15 を列挙している。直前の Phase 0 PR #3 は本番投入前ブロッカーを解消したが、P1 の入口である DynamoDB repository の Query 化、job idempotency、JobEvent 由来の lifecycle、`static_export` の完了追跡がまだ十分ではない。

## 目的

YouTube metadata → chat collect → normalize → aggregate → artifacts → static export の一連の実データ pipeline を進める前提として、DynamoDB read/write model と job 状態管理を本番向けに近づける。

## スコープ

- 対象: `apps/shared/src/diopside_core/repository.py`、関連 tests、README、作業レポート。
- 対象 P1: P1-01、P1-02、P1-03、P1-04。
- 対象外: 実 AWS deploy、実 DynamoDB への接続、実 YouTube API 呼び出し、P1-05 以降の collector 実データ拡張。

## 実施計画

1. DynamoDB repository の `list_videos`、`list_jobs`、`list_quota_usage` を Query + pagination へ寄せる。
2. Job idempotency を DynamoDB 条件付き書き込みで保証できる形にする。
3. `derived_state` を保存値に依存せず JobEvent の末尾から導出する helper を整理する。
4. `static_export` の worker 完了追跡が repository lifecycle と整合していることを test で固定する。
5. README に P1 範囲の DynamoDB access pattern と job idempotency/lifecycle の説明を反映する。

## ドキュメント保守計画

- README の DynamoDB item schema / access pattern / job lifecycle 説明を更新する。
- `docs/` は既存構成上まだ要求分割されていないため、今回の小規模 repository 実装更新では README を durable doc として更新する。

## 受け入れ条件

- [x] P1-01: `DynamoRepository.list_videos`、`list_jobs`、`list_quota_usage` が通常経路で `scan` に依存せず、GSI Query + pagination を使う。
  - 根拠: `apps/shared/src/diopside_core/repository.py`、`tests/test_core_pipeline.py::test_dynamo_repository_lists_use_query_indexes`。
- [x] P1-02: 同一 `idempotency_key` の同時 `create_job` で Job と JobEvent が二重作成されないよう、DynamoDB 条件付き書き込みまたは専用 idempotency item で保証される。
  - 根拠: `DynamoRepository.create_job` の `ConditionExpression=\"attribute_not_exists(pk)\"`、`tests/test_core_pipeline.py::test_dynamo_create_job_condition_prevents_duplicate_events`。
- [x] P1-03: Job の `derived_state` は保存値ではなく、`JobEvent` の末尾イベントから導出される。
  - 根拠: `derive_job_state` と `get_job`、`tests/test_core_pipeline.py::test_repository_job_idempotency_and_lists`。
- [x] P1-04: `static_export` worker が処理時に `JobEvent` の `started` と `completed` を追記することが test で確認できる。
  - 根拠: PR #3 由来の `static_exporter.handler` と `tests/test_static_exporter.py::test_static_export_job_records_completion`。
- [x] README に Query 化、idempotency、JobEvent lifecycle の運用・設計説明が反映されている。
  - 根拠: `README.md`。
- [x] 変更範囲に応じた tests と `npm run verify` が成功する。

## 検証計画

- `git diff --check`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_static_exporter.py`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_static_exporter.py`: pass
- `npm test`: pass
- `npm run verify`: pass

## PRレビュー観点

- DynamoDB scan が通常経路に残っていないこと。
- Job の状態が保存値ではなくイベント列から導出されること。
- idempotency item と Job/JobEvent の整合が崩れないこと。
- P0 PR #3 上に積んだ差分であることを PR 本文に明記すること。

## リスク

- この branch は PR #3 の branch を土台にした stacked worktree であり、PR #3 が merge されるまで main との差分には P0 変更も含まれる。
- 実 DynamoDB への接続は行わないため、DynamoDB API 呼び出し形状は stub/fake による検証に留まる。
