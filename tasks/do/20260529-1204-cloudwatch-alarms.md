# 最低限のCloudWatch Alarm

状態: do

## 背景

`.workspace/plan-20260529.txt` の P2-07 に従い、DLQ depth、Lambda error、API 5xx、static export failure を CloudWatch Alarm 化する。

## 目的

本番 deploy 後に最低限の障害兆候を検知できるよう、CloudFormation template に CloudWatch Alarm を追加し、alarm 対象と調査導線を README に明記する。

## タスク種別

機能追加

## スコープ

- CloudFormation の CloudWatch Alarm resource 追加
- DLQ depth、Lambda error、API 5xx、static export failure の contract test 追加
- README の alarm 運用方針追記
- 実 SNS 通知先の追加は対象外。alarm action は未設定で、CloudWatch console / EventBridge 連携の前提まで記載する。

## 計画

1. 既存 CloudFormation の Lambda / SQS / API origin 構成を確認する。
2. CloudWatch Alarm resource を追加する。
3. Contract test で metric name、namespace、dimensions、threshold を検証する。
4. README に alarm 一覧、発火時の初動、未設定の通知先制約を追記する。
5. 検証、作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

運用監視の挙動が増えるため、README の運用 section に alarm 一覧と調査導線を追記する。通知先未設定の制約は明記する。

## 受け入れ条件

- DLQ depth alarm が各 DLQ の `ApproximateNumberOfMessagesVisible >= 1` を検知する。
- Lambda error alarm が API Lambda と worker Lambda の `Errors >= 1` を検知する。
- API 5xx alarm が API Lambda の 5xx 相当を検知できる。
- static export failure alarm が static export 失敗を検知できる。
- CloudFormation contract test が alarm の namespace、metric、dimensions、threshold を検証する。
- README に alarm 一覧、発火時の初動、通知先未設定の制約が記載されている。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- `python3 -m pytest tests/test_cloudformation_contract.py`
- `npm test`
- 必要に応じて `npm run verify`

## PRレビュー観点

- Alarm が高コストなサービスを追加していないこと。
- Dimensions が CloudFormation resource と整合していること。
- 通知先を設定していない制約を実施済み扱いしていないこと。

## リスク

- Function URL origin では API Gateway の 5xx metric は使えないため、API 5xx は API Lambda 側の error metric または log metric filter のどちらで検知するかを実装時に確認する。
- 実 CloudWatch alarm の発火確認は実 AWS deploy 後の確認事項として残る。
