# CDK parity bootstrap 作業完了レポート

## 受けた指示

`.workspace/plan-20260530.txt` と `.workspace/` の v0.4 設計書を正本として、main を pull 済みの作業ブランチで v0.4 準拠を継続する。今回は P0-03 IaC の AWS CDK 正本化に向け、CDK parity bootstrap を進めた。

## 要件整理

- 現 `infra/cloudformation/diopside.yaml` を落とさず、CDK app から synth できる状態を作る。
- CDK synth output が現 CloudFormation と主要 resource parity を保つことを検査する。
- CDK bootstrap 済みと、L2 construct 分解 / deploy runbook 完全切替 / 実 deploy rehearsal の残課題を区別する。
- 実施していない AWS deploy を実施済みとして書かない。

## 検討・判断

- 初回の CDK 化は `aws-cdk-lib/cloudformation-include` の `CfnInclude` を使い、現 CloudFormation template をそのまま CDK synth する方式にした。
- これにより logical ID / resource type の parity を保ちつつ、以後の Edge/Data/Api/Collector/Observability construct 分解へ進める土台を作る。
- `npm run cdk:synth` は `build/cdk.out/DiopsideStack.template.json` を生成する。`build/` は既存 `.gitignore` の対象なので synth output は commit しない。

## 実施作業

- `aws-cdk-lib` と `constructs` を dev dependency に追加した。
- `cdk.json` と `infra/cdk/bin/diopside-cdk.mjs` を追加した。
- `infra/cdk/README.md` に bootstrap の位置づけと synth 手順を記載した。
- `tests/test_cdk_contract.py` を追加し、CDK synth output と現 CloudFormation の resource logical ID / type parity、v0.4 serverless resource families、package script を検査した。
- README の deploy runbook を `npm run cdk:synth` と `build/cdk.out/DiopsideStack.template.json` 基準へ更新した。
- `docs/design/traceability-matrix.md` と `reports/audit/design-v0.4-compliance-20260530.md` の IaC 状態を、CDK bootstrap 済み / construct 分解は後続に更新した。

## 成果物

- `cdk.json`
- `infra/cdk/bin/diopside-cdk.mjs`
- `infra/cdk/README.md`
- `tests/test_cdk_contract.py`
- README / traceability / audit 更新
- `tasks/do/20260530-1928-cdk-parity-bootstrap.md`

## 検証

- `npm run cdk:synth`
  - pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py tests/test_cdk_contract.py`
  - 19 passed
- `node tools/check-docs-consistency.mjs`
  - passed
- `git diff --check`
  - passed
- `npm run verify`
  - 143 passed、build、package、local e2e passed

## 指示への fit 評価

- v0.4 の P0-03 IaC gap に対し、現 CloudFormation を移行元として CDK synth できる実体と parity gate を追加した。
- ただし、CDK L2 construct への全面移行、CloudFormation template の生成物化、実 AWS deploy rehearsal は未完了であり、完全な IaC 正本化までは残作業がある。

## 未対応・制約・リスク

- `CfnInclude` bootstrap であり、Edge/Data/Api/Collector/Observability construct への分割は未対応。
- 実 AWS CDK deploy / CloudFormation deploy は未実施。
- `npm install` 後に npm audit が moderate vulnerability 1 件を報告したが、今回の scope では audit fix は実施していない。
