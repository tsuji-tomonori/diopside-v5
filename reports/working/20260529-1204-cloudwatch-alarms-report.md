# 最低限のCloudWatch Alarm 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan ファイルに基づき、main から pull してから作業する。
- P2-07 `最低限のAlarm` として、DLQ depth、Lambda error、API 5xx、static export failure を CloudWatch Alarm 化する。

## 要件整理

- CloudFormation に最低限の CloudWatch Alarm を追加する。
- DLQ depth、API Lambda error、worker Lambda error、API 5xx、static export failure を検知対象にする。
- Alarm の namespace、metric、dimensions、threshold を contract test で確認する。
- README に alarm 一覧、発火時の初動、通知先未設定の制約を記載する。

## 検討・判断

- Function URL origin では API Gateway の 5xx metric が使えないため、P2-06 で追加した API JSON log から `Api5xxCount` metric filter を作る構成にした。
- static export failure は static export 専用 Lambda の `AWS/Lambda Errors` で検知する構成にした。
- 個人開発向けの初期構成として SNS topic などの通知先は固定せず、alarm action 未設定の制約を README と PR に明記する方針にした。
- CloudWatch Logs の保持期間を明示するため、API / worker / static exporter の log group を 30 日 retention で CloudFormation 管理にした。

## 実施作業

- `infra/cloudformation/diopside.yaml` に API / worker / static exporter の `AWS::Logs::LogGroup` を追加した。
- API 5xx 用の `AWS::Logs::MetricFilter` と `Api5xxAlarm` を追加した。
- 5 つの DLQ depth alarm を追加した。
- API / worker / static export Lambda error alarm を追加した。
- `tests/test_cloudformation_contract.py` に log group、metric filter、alarm contract test を追加した。
- `README.md` に CloudWatch Alarm 一覧、初動、通知先未設定の制約を追記した。
- `tasks/do/20260529-1204-cloudwatch-alarms.md` を作成した。

## 成果物

- `infra/cloudformation/diopside.yaml`
- `tests/test_cloudformation_contract.py`
- `README.md`
- `tasks/do/20260529-1204-cloudwatch-alarms.md`

## 検証

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py`: 13 passed
- `npm test`: 57 passed
- `npm run verify`: 成功

## fit 評価

- P2-07 が指定する DLQ depth、Lambda error、API 5xx、static export failure の CloudWatch Alarm 化を CloudFormation と contract test で満たした。
- 実 AWS での alarm 発火確認と通知先設定は未実施のため、運用上の残タスクとして明記した。

## 未対応・制約・リスク

- 実 AWS 環境での CloudWatch Alarm 作成、発火、通知は未確認。
- 初期構成では alarm action を設定していないため、通知が必要な場合は deploy 後に SNS topic などを関連付ける必要がある。
