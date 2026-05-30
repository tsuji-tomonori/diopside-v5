# GitHub Actions JobMessage dispatch

状態: done

## 背景

v0.4 は BATCH-020 の手動ジョブディスパッチとして、管理 API に加えて GitHub Actions `workflow_dispatch` からの投入を想定している。現 repository には CI workflow のみがあり、手動で SQS へ v0.4 `JobMessage` を送る workflow がない。

## 目的

GitHub Actions `workflow_dispatch` から v0.4 `JobMessage` schema の SQS message を投入できる最小 workflow を追加する。

## タスク種別

機能追加

## スコープ

- `.github/workflows/manual-job-dispatch.yml` を追加する。
- workflow は `job_type`、`idempotency_key`、`payload_json` を入力に取り、queue URL secret へ routing して `aws sqs send-message` する。
- workflow の message body は `job_id`、`job_type`、`idempotency_key`、`requested_by=github_actions`、`attempt`、`trace_id`、`payload` を持つ。
- workflow contract test と README / worker batch audit / traceability を更新する。

## 計画

1. 既存 workflow と queue env mapping を確認する。
2. manual dispatch workflow を追加する。
3. workflow contract test を追加する。
4. README / worker batch audit / traceability を更新する。
5. 対象検証と `npm run verify` を実行する。

## ドキュメント保守方針

README の worker / job dispatch 記述、`docs/design/worker-batch-coverage-audit.md` の BATCH-020、`docs/design/traceability-matrix.md` の BATCH-020 evidence を更新する。

## 受け入れ条件

- `workflow_dispatch` workflow が存在し、手動 job_type と payload_json を入力できる。
- workflow が v0.4 `JobMessage` field を組み立てる。
- workflow が job_type から metadata/chat/normalize/aggregate/static-export queue URL secret へ routing する。
- workflow が GitHub OIDC で AWS role を引き受け、長期 AWS key を要求しない。
- contract test が workflow の v0.4 `JobMessage` field と queue routing を検証する。
- README、worker batch audit、traceability が更新済みである。
- 選定した検証コマンドが pass し、未実施検証があれば理由を記録する。

## 検証計画

- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_github_workflows_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- workflow が repository secret に長期 AWS access key を要求していないこと。
- `payload_json` を `jq` で JSON として検証してから message body に入れていること。
- workflow が実行時のみ外部 SQS を変更し、PR/CI では実行されないこと。

## リスク

- workflow は手動実行時に実 AWS SQS へ message を送るため、運用者は target queue secret と role scope を正しく設定する必要がある。

## 完了結果

- `.github/workflows/manual-job-dispatch.yml` を追加し、GitHub Actions `workflow_dispatch` から v0.4 `JobMessage` を SQS へ送れるようにした。
- `job_type` から metadata/chat/normalize/aggregate/static-export queue URL secret へ routing する contract を追加した。
- GitHub OIDC role assumption を使い、長期 AWS access key を要求しない workflow とした。
- README、worker batch audit、traceability matrix を更新した。
- 作業レポート: `reports/working/20260530-1708-github-actions-job-dispatch.md`
- PR 受け入れ条件コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582230552
- PR セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582230533

## 検証結果

- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_github_workflows_contract.py`: pass（2 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（134 tests + build/package/local e2e）

## 未実施・制約

- 実 AWS での `workflow_dispatch`: 未実施。理由: 手動実行時に実 SQS へ送信するため、運用環境の queue secrets / OIDC role 設定後に実施する。
