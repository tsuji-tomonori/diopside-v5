# cost guard

状態: do

## 背景

`.workspace/plan-20260529.txt` の P4-06 に従い、固定費の高いサービス、SQL 系 DB、OpenSearch、ECS、EC2 が CloudFormation に混入していないことを contract test で検出する。

## 目的

低コスト構成の前提を CloudFormation contract として固定し、意図しない固定費サービス追加を CI で検出できるようにする。

## タスク種別

infrastructure contract test

## スコープ

- `tests/test_cloudformation_contract.py`

## 計画

1. 現行 CloudFormation resource type と contract test を確認する。
2. 高固定費 service / SQL DB / OpenSearch / ECS / EC2 系 resource type の禁止リストを追加する。
3. CloudFormation parse test と `npm test` / `npm run verify` で CI 対象に入ることを確認する。
4. 作業レポート、commit、PR、受け入れ条件コメント、セルフレビューまで完了する。

## ドキュメント保守方針

インフラ contract test の追加であり README 更新は不要の見込み。禁止対象と未実施の実 AWS cost 確認は task md と作業レポートに残す。

## 受け入れ条件

- SQL 系 DB / RDS 系 resource が CloudFormation に含まれないことを contract test で検出する。
- OpenSearch / Elasticsearch domain が CloudFormation に含まれないことを contract test で検出する。
- ECS / EKS が CloudFormation に含まれないことを contract test で検出する。
- EC2 / VPC / NAT / LoadBalancer 系の固定費 resource が CloudFormation に含まれないことを contract test で検出する。
- 追加テストが `npm test`、ひいては CI の `npm run verify` で実行される。
- 変更範囲に見合う検証が成功する。

## 検証計画

- `git diff --check`
- targeted pytest
- `npm test`
- `npm run verify`

## リスク

- 実 AWS Cost Explorer / 見積もり API は使用せず、CloudFormation resource type の静的 contract に限定する。
