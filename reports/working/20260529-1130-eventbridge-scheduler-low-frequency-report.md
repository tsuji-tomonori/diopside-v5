# EventBridge Scheduler 低頻度起動追加 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan ファイルに基づき、main から pull してから作業する。
- P2-04 `EventBridge Scheduler追加` として、metadata sync、live status scan、quota rollup、cleanup の定期起動を追加する。

## 要件整理

- EventBridge Scheduler から SQS へ低頻度で job payload を投入する。
- Scheduler 用 IAM role は対象 queue への `sqs:SendMessage` に限定する。
- `quota_rollup` と `cleanup` を worker が受け付け、cleanup は実削除なしの安全な report に留める。
- CloudFormation contract test と worker test で schedule、payload、権限、handler 動作を検証する。
- README に運用方針を追記する。

## 検討・判断

- 個人開発向けの低頻度設定として、`metadata_sync` は 12 時間、`live_status_scan` は 30 分、`quota_rollup` は 1 日、`cleanup` は 7 日に設定した。
- 定期投入先は既存 queue 構成に合わせ、metadata 系を `MetadataQueue`、maintenance/aggregate 系を `AggregateQueue` にした。
- cleanup は `dry_run` 入力に関わらず常に `deleted_count=0` とし、現時点で削除副作用を持たせない設計にした。

## 実施作業

- `infra/cloudformation/diopside.yaml` に `SchedulerRole` と 4 つの `AWS::Scheduler::Schedule` を追加した。
- `apps/workers/static-exporter/src/static_exporter/pipeline.py` に `quota_rollup` / `cleanup` の dispatch と handler を追加した。
- `tests/test_cloudformation_contract.py` に Scheduler role と schedule payload/target/rate の contract test を追加した。
- `tests/test_core_pipeline.py` に maintenance job の handler/dispatch test を追加した。
- `README.md` に EventBridge Scheduler の頻度、投入先、IAM 制約、cleanup 方針を追記した。
- task md を `tasks/do/20260529-1130-eventbridge-scheduler-low-frequency.md` として作成した。

## 成果物

- `infra/cloudformation/diopside.yaml`
- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_cloudformation_contract.py`
- `tests/test_core_pipeline.py`
- `README.md`
- `tasks/do/20260529-1130-eventbridge-scheduler-low-frequency.md`

## 検証

- `git diff --check`: 成功
- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py tests/test_core_pipeline.py`: 38 passed
- `npm test`: 51 passed
- `npm run verify`: 成功

## fit 評価

- plan P2-04 の対象 job 4 種類を低頻度 Scheduler として追加し、受け入れ条件を contract test と worker test で確認できる状態にした。
- README に運用方針を追記し、docs と実装の同期を保った。

## 未対応・制約・リスク

- 実 AWS 環境への deploy と EventBridge Scheduler 実発火は未実施。
- cleanup は安全性優先で report-only とし、実削除 policy は未実装。
