# GitHub Actions JobMessage dispatch report

## 指示

- `.workspace/plan-20260530.txt` と `.workspace/` の設計書に沿って v0.4 対応を進める。
- repository の Worktree Task PR Flow に従い、task md、実装、検証、PR 更新、作業レポートを残す。
- 実施していない検証を実施済みとして書かない。

## 要件整理

| 要件ID | 要件 | 対応状況 |
|---|---|---|
| R1 | GitHub Actions `workflow_dispatch` から手動 job dispatch できる workflow を追加する | 対応 |
| R2 | workflow が v0.4 `JobMessage` field を組み立てる | 対応 |
| R3 | job_type から queue URL secret へ routing する | 対応 |
| R4 | GitHub OIDC で AWS role を引き受け、長期 AWS key を要求しない | 対応 |
| R5 | workflow contract test と docs を更新する | 対応 |

## 検討・判断

- PR/CI で外部 state を変えないよう、workflow は `workflow_dispatch` の手動実行限定にした。
- AWS 認証は `aws-actions/configure-aws-credentials@v4` と GitHub OIDC を使い、long-lived AWS access key secret は使わない。
- `payload_json` は shell step で `jq -e .` により JSON として検証してから `payload` に入れる。
- queue URL は job_type ごとに repository secret から選択し、未設定なら実行を失敗させる。

## 実施作業

- `.github/workflows/manual-job-dispatch.yml` を追加した。
- `tests/test_github_workflows_contract.py` を追加し、workflow input、OIDC permission、JobMessage field、queue routing を検証した。
- README、worker batch audit、traceability の BATCH-020 evidence と残課題を更新した。

## 成果物

| 成果物 | 内容 |
|---|---|
| `.github/workflows/manual-job-dispatch.yml` | GitHub Actions 手動 job dispatch workflow |
| `tests/test_github_workflows_contract.py` | workflow contract test |
| `README.md` | GitHub Actions dispatch 設定と JobMessage 記述 |
| `docs/design/worker-batch-coverage-audit.md` | BATCH-020 と現 worker contract 更新 |
| `docs/design/traceability-matrix.md` | BATCH-020 evidence 更新 |
| `tasks/do/20260530-1708-github-actions-job-dispatch.md` | 受け入れ条件と検証計画 |

## 実行した検証

- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_github_workflows_contract.py`: pass, 2 passed
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass, 134 pytest passed + build/package/e2e pass

## 未対応・制約・リスク

- 実 AWS での workflow_dispatch 実行は未実施。queue secret、OIDC role、AWS account は運用環境で設定が必要。
- 手動実行時は実 SQS に message を送るため、運用者が payload と idempotency key を確認して実行する必要がある。

## Fit 評価

総合fit: 4.8 / 5.0

理由: GitHub Actions workflow_dispatch 経路を v0.4 `JobMessage` で追加し、契約テストと docs を更新した。実 AWS dispatch rehearsal は未実施のため満点ではない。
