# Scheduler JobMessage v0.4 schema alignment report

## 指示

- `.workspace/plan-20260530.txt` と `.workspace/` の設計書に沿って v0.4 対応を進める。
- repository の Worktree Task PR Flow に従い、task md、実装、検証、PR 更新、作業レポートを残す。
- 実施していない検証を実施済みとして書かない。

## 要件整理

| 要件ID | 要件 | 対応状況 |
|---|---|---|
| R1 | EventBridge Scheduler target input を v0.4 `JobMessage` field へ寄せる | 対応 |
| R2 | schedule 固有 field を `payload` に入れる | 対応 |
| R3 | CloudFormation contract test を更新する | 対応 |
| R4 | README と worker batch audit を更新する | 対応 |

## 検討・判断

- 管理 API / worker 後続投入と同じ `JobMessage` required fields を Scheduler input に追加した。
- Scheduler placeholder `<aws.scheduler.execution-id>` と `<aws.scheduler.scheduled-time>` は維持し、`job_id` / `trace_id` / `idempotency_key` の根拠にした。
- `max_results` や `dry_run` は batch 固有 payload として `payload` に移した。
- IAM resource scope、schedule cadence、queue target は変更していない。

## 実施作業

- `infra/cloudformation/diopside.yaml` の `MetadataSyncSchedule`、`LiveStatusScanSchedule`、`QuotaRollupSchedule`、`CleanupSchedule` target input を v0.4 `JobMessage` shape へ更新した。
- `tests/test_cloudformation_contract.py` の schedule input assertions を `payload` / `idempotency_key` / `trace_id` / `attempt` 中心に更新した。
- README、worker batch audit、traceability の Scheduler JobMessage 記述を更新した。

## 成果物

| 成果物 | 内容 |
|---|---|
| `infra/cloudformation/diopside.yaml` | Scheduler target input の v0.4 `JobMessage` 化 |
| `tests/test_cloudformation_contract.py` | Scheduler message contract 更新 |
| `README.md` | worker / Scheduler message contract 記述更新 |
| `docs/design/worker-batch-coverage-audit.md` | BATCH-020 と後続課題更新 |
| `docs/design/traceability-matrix.md` | BATCH-020 evidence 更新 |
| `tasks/do/20260530-1658-scheduler-job-message-v04.md` | 受け入れ条件と検証計画 |

## 実行した検証

- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py`: pass, 16 passed
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass, 132 pytest passed + build/package/e2e pass

## 未対応・制約・リスク

- GitHub Actions workflow_dispatch 由来の message fields 統一は未対応。
- 新 Scheduler template と旧 worker code を混在 deploy する場合、旧 worker は `payload` field を読めない可能性がある。現 PR branch の worker は新旧両方を処理できる。

## Fit 評価

総合fit: 4.8 / 5.0

理由: Scheduler target input を v0.4 `JobMessage` へ整合し、contract test と docs を更新した。GitHub Actions workflow_dispatch 側は後続対象として残したため満点ではない。
