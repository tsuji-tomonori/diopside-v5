# Scheduler JobMessage v0.4 schema alignment

状態: done

## 背景

管理 API と worker 後続投入は v0.4 `JobMessage` field へ寄せたが、CloudFormation の EventBridge Scheduler target input は旧 `input` field 形式のまま残っている。

## 目的

EventBridge Scheduler が SQS へ送る定期 job message を v0.4 `JobMessage` schema へ合わせる。

## タスク種別

機能追加

## スコープ

- `infra/cloudformation/diopside.yaml` の scheduler input を `payload` / `requested_by` / `attempt` / `trace_id` 付きへ更新する。
- CloudFormation contract test の schedule input 期待値を更新する。
- README / worker batch audit の Scheduler message 差分記述を更新する。

## 計画

1. 現 scheduler input と contract test を確認する。
2. metadata/live/quota/cleanup schedule の input JSON を v0.4 `JobMessage` field へ更新する。
3. contract test を `payload` field 中心へ更新する。
4. docs の後続課題から Scheduler template 未整合を外す。
5. 対象検証と `npm run verify` を実行する。

## ドキュメント保守方針

`README.md` と `docs/design/worker-batch-coverage-audit.md` の JobMessage / Scheduler 未整合記述を実装状況に合わせて更新する。

## 受け入れ条件

- 4 つの EventBridge Scheduler target input が `job_id`、`job_type`、`idempotency_key`、`requested_by=scheduler`、`attempt`、`trace_id`、`payload` を持つ。
- schedule 固有 field は `payload` に入る。
- CloudFormation contract test が v0.4 `JobMessage` shape を検証する。
- README と worker batch audit が更新済みである。
- 選定した検証コマンドが pass し、未実施検証があれば理由を記録する。

## 検証計画

- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- Schedule input が v0.4 `JobMessage` required fields を満たすこと。
- Scheduler placeholder の `<aws.scheduler.execution-id>` / `<aws.scheduler.scheduled-time>` が維持されること。
- IAM scope や schedule cadence を広げていないこと。

## リスク

- 既存 worker は新 `payload` field を受け付けるため互換は維持されるが、deploy 済みの旧 worker と新 scheduler template を混在させる場合は旧 worker が `payload` を読めない可能性がある。

## 完了結果

- PR 受け入れ条件コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582204853
- PR セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582204867
- 作業レポート: `reports/working/20260530-1658-scheduler-job-message-v04.md`
- 検証: `npm run verify` pass（132 tests + build/package/local e2e）
