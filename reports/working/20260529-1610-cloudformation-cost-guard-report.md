# cost guard 作業レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づいて作業する。
- `main` から pull してから、P4-06 cost guard を進める。
- Worktree Task PR Flow に従い、task、検証、PR コメントまで行う。

## 要件整理

- 固定費の高いサービス、SQL 系 DB、OpenSearch、ECS、EC2 が CloudFormation に混入していないことを contract test で検出する。
- 追加テストは `npm test`、ひいては CI の `npm run verify` で実行される必要がある。

## 検討・判断

- CloudFormation の `Resources.*.Type` を静的に検査する contract test とした。
- RDS / DocDB / Neptune / Redshift / OpenSearch / Elasticsearch / ECS / EKS / EC2 / Load Balancer / ElastiCache を禁止 prefix とした。
- DynamoDB / S3 / SQS / Lambda / CloudFront / Scheduler / CloudWatch は現行構成として許容する。

## 実施作業

- `tests/test_cloudformation_contract.py` に cost guard の禁止 resource type test を追加した。
- P4-06 の task md を作成した。

## 成果物

- `tests/test_cloudformation_contract.py`
- `tasks/do/20260529-1610-cloudformation-cost-guard.md`

## 検証

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py -k cost_guard`: 1 passed
- `npm test`: 70 passed
- `npm run verify`: 成功
  - `npm test`: 70 passed
  - `npm run build`: 成功
  - `npm run package:deploy`: 成功
  - `npm run e2e:local`: 成功

## fit 評価

- P4-06 の cost guard contract test 追加要求に対応した。
- 追加テストは `npm test` に含まれるため、P4-01 の GitHub Actions CI の `npm run verify` で実行される。

## 未対応・制約・リスク

- 実 AWS Cost Explorer / 見積もり API は使用せず、CloudFormation resource type の静的 contract に限定した。
- PR 作成後、GitHub Actions 上の `CI / npm verify` 成功を確認する必要がある。
