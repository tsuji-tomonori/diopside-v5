# BATCH-006 notification delivery state 作業完了レポート

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-05-30 |
| 対象 | `.workspace/plan-20260530.txt` v0.4 設計準拠対応 |
| task | `tasks/do/20260530-1919-batch006-notification-delivery.md` |

## 受けた指示

`.workspace/plan-20260530.txt` と `.workspace/` 配下の設計書に基づき、`main` を pull した上で v0.4 設計準拠対応を進める。

## 要件整理

- BATCH-006 は NotificationPlan の作成だけでなく、通知対象時に sent/skipped/failed を記録する必要がある。
- v0.4 は SNS/Discord/Email などの外部通知を任意としているため、target 未設定は失敗ではなく skipped とする。
- 実 SNS/Discord/Email 疎通と物理 DLQ はこの環境では実施しない。

## 検討・判断

`notification_plan` は future due の plan 作成にも使われているため、due 未到達の plan は `planned` のままにした。due 済み plan だけ delivery state を進め、target 未設定は `skipped`、injected client または SNS delivery 成功は `sent`、送信例外は `failed` とする。

テストでは実外部通信を使わず、injected notification client で成功・失敗を検証した。実運用向けには `DIOPSIDE_NOTIFICATION_SNS_TOPIC_ARN` がある場合に SNS publish できる adapter を追加した。

## 実施作業

- `notification_plan` に due 判定と delivery state 更新を追加した。
- target 未設定、delivery 成功、delivery 失敗の tests を追加した。
- BATCH-006 / NotificationPlan の worker audit、DDB audit、README、compliance audit を更新した。

## 成果物

- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_core_pipeline.py`
- `README.md`
- `docs/design/worker-batch-coverage-audit.md`
- `docs/design/dynamodb-schema-audit.md`
- `reports/audit/design-v0.4-compliance-20260530.md`
- `tasks/do/20260530-1919-batch006-notification-delivery.md`
- `reports/working/20260530-1919-batch006-notification-delivery.md`

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_notification_plan_creates_due_items_idempotently tests/test_core_pipeline.py::test_notification_plan_delivers_due_items_and_records_states tests/test_repository_schema_contract.py::test_repository_accepts_notification_plan_v04_item_shape`
  - 3 passed
- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`
  - passed
- `node tools/check-docs-consistency.mjs`
  - passed
- `git diff --check`
  - passed
- `npm run verify`
  - 140 passed、build、package、local e2e passed

## fit 評価

- BATCH-006 の sent/skipped/failed read model 更新を実装し、NotificationPlan の v0.4 schema に近づけた。
- 実 SNS/Discord/Email 疎通、物理通知 DLQ、due 再投入は未実施として明記した。
- `.workspace/plan-20260530.txt` 全体の残課題は継続中であり、本レポートは BATCH-006 delivery state のみを完了対象とする。

## 未対応・制約・リスク

- 実 SNS / Discord / Email への送信は未確認。
- 物理通知 DLQ は未実装。
- EventBridge one-shot / SQS delay による due 再投入は未実装。
- dev 環境、CloudFront、実 YouTube データでの rehearsal は未実施。
