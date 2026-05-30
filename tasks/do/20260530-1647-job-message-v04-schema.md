# JobMessage v0.4 schema alignment

状態: do

## 背景

`docs/design/diopside_basic_design_v0.4.md` の 9.7 では SQS message 共通 schema `JobMessage` が定義されている。現状の管理 API と worker の後続投入 message は `job_id` / `job_type` / `input` を中心にしており、`idempotency_key`、`requested_by`、`attempt`、`payload` が共通 field として揃っていない。

## 目的

既存 worker 互換を維持しながら、管理 API と worker の SQS enqueue payload を v0.4 `JobMessage` field へ寄せる。

## タスク種別

機能追加

## スコープ

- `JobMessage` を組み立てる shared helper を追加する。
- 管理 API の job enqueue message を v0.4 shape に寄せる。
- worker pipeline の後続 job enqueue message を v0.4 shape に寄せる。
- worker dispatch は既存 `input` message と新 `payload` message の両方を受け付ける。
- README / worker batch audit / traceability を更新する。

## 計画

1. v0.4 `JobMessage` required fields と現 enqueue 箇所を確認する。
2. shared helper で `job_id`、`job_type`、`idempotency_key`、`requested_by`、`attempt`、`trace_id`、`payload` を正規化する。
3. API `_start_job` と pipeline `_enqueue_job` 呼び出し箇所を helper 経由に寄せる。
4. `dispatch_job` の新旧 message 互換を維持する。
5. API / worker tests と docs を更新する。
6. 対象検証と `npm run verify` を実行する。

## ドキュメント保守方針

`docs/design/worker-batch-coverage-audit.md` の BATCH-020 と現 worker contract、`docs/design/traceability-matrix.md` の BATCH-020、README の worker 差分説明を更新する。

## 受け入れ条件

- 管理 API が queue へ送る message に `job_id`、`job_type`、`idempotency_key`、`requested_by=admin`、`attempt`、`trace_id`、`payload` が含まれる。
- worker の後続投入 message に `payload` と `requested_by=worker` が含まれる。
- `dispatch_job` が v0.4 `payload` field と旧 `input` field の両方を処理できる。
- 既存の worker/API テストが通り、新しい message contract test が追加される。
- README、worker batch audit、traceability が更新済みである。
- 選定した検証コマンドが pass し、未実施検証があれば理由を記録する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/api/src/diopside_api/handler.py apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py`
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_worker_batch_coverage_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- 新 `payload` field へ寄せても旧 `input` message が破壊されないこと。
- `idempotency_key` と `attempt` が推測可能な範囲で一貫していること。
- SQS message に大きな本文や機微情報を追加していないこと。

## リスク

- 既存外部 producer が旧 `input` 形式で投入している可能性があるため、dispatch 互換を維持する。
- worker 起点の downstream job は親 job の idempotency key がない場合があるため、安定した fallback key を使う。
