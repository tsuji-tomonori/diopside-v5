# CDK parity bootstrap

状態: done

タスク種別: 機能追加

## 背景

`.workspace/plan-20260530.txt` は v0.4 完全実装の構造的ブロッカーとして、IaC 正本を AWS CDK に寄せることを P0-03 に置いている。現 worktree の infra は `infra/cloudformation/diopside.yaml` のみで、CDK app、CDK synth script、CDK synth output に対する parity 検査がない。

## 目的

現 CloudFormation template を移行元として CDK app から synth できる状態を作り、以後の infra 変更を CDK 正本へ寄せるための最初の parity gate を追加する。

## スコープ

- `infra/cdk/` に CDK app を追加する。
- 現 `infra/cloudformation/diopside.yaml` を CDK へ include し、synth output を生成できる npm script を追加する。
- synth output が現 CloudFormation と主要 resource parity を保つことを contract test で確認する。
- README / design audit / traceability を CDK bootstrap 済みの状態に更新する。
- 作業完了レポートを作成する。

## スコープ外

- L2 construct への全面分解。
- CloudFormation template の削除または生成物扱いへの完全移行。
- deploy runbook の CDK deploy 完全切替。
- 実 AWS deploy rehearsal。

## 計画

1. 既存 CloudFormation contract と package script を確認する。
2. CDK dependency、CDK app、`cdk:synth` script を追加する。
3. CDK synth output と現 CloudFormation の parity test を追加する。
4. README と監査 docs を更新し、targeted checks と `npm run verify` を実行する。
5. PR 本文・コメント、task done、push まで完了する。

## ドキュメント保守計画

- README の infra / deploy 説明に CDK synth を追加し、CloudFormation が移行元 template であることを明記する。
- `docs/design/traceability-matrix.md` と `reports/audit/design-v0.4-compliance-20260530.md` の IaC gap を、CDK bootstrap 済み・L2 construct 分解は後続の状態へ更新する。

## 受け入れ条件

- [x] `infra/cdk/` に CDK app が存在する。
- [x] `npm run cdk:synth` が成功し、CDK synth output が生成される。
- [x] CDK synth output が CloudFront、S3 buckets、DynamoDB table、SQS/DLQ、Scheduler、Lambda、IAM、CloudWatch Alarm の主要 resource type を含む。
- [x] 現 CloudFormation template と CDK synth output の resource logical id / type が一致する。
- [x] 既存 CloudFormation contract tests が引き続き通る。
- [x] docs / audit が「CDK bootstrap 済み」と残る infra gap を区別している。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `npm run cdk:synth`
  - passed
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py tests/test_cdk_contract.py`
  - 19 passed
- `node tools/check-docs-consistency.mjs`
  - passed
- `git diff --check`
  - passed
- `npm run verify`
  - 143 passed、build、package、local e2e passed

## 検証計画

- `npm run cdk:synth`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py tests/test_cdk_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- CDK app が v0.4 の AWS CDK 正本化に向かう実体になっていること。
- 現行 infra resource を落とさず parity gate があること。
- CDK bootstrap を完了以上に過大申告せず、L2 construct 分解や deploy 切替を後続と明記していること。

## リスク

- `aws-cdk-lib` / `constructs` 追加により npm install 時間と package-lock が増える。
- 今回は `CfnInclude` による bootstrap であり、construct 分割や CDK deploy rehearsal は未完了。

## Done 条件

- 実装、テスト、docs 更新、作業レポート作成、PR 本文更新を完了した。
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582549277
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582549475
