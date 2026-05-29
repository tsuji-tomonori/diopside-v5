# EventBridge Scheduler追加

状態: done

## 背景

`.workspace/plan-20260529.txt` の P2-04 に従い、metadata sync、live status scan、quota rollup、cleanup の定期起動を EventBridge Scheduler で追加する。個人開発向けに頻度は低めにする。

## 受け入れ条件

- EventBridge Scheduler 用 IAM role が定義され、対象 SQS queue への `sqs:SendMessage` のみに限定される。
- metadata sync の低頻度 schedule が metadata queue に `job_type=metadata_sync`、`requested_by=scheduler` を送る。
- live status scan の低頻度 schedule が metadata queue に `job_type=live_status_scan`、`requested_by=scheduler` を送る。
- quota rollup の日次 schedule が worker queue に `job_type=quota_rollup`、`requested_by=scheduler` を送る。
- cleanup の週次 schedule が worker queue に `job_type=cleanup`、`requested_by=scheduler` を送る。
- worker が `quota_rollup` と `cleanup` を失敗させず、実削除なしの安全な結果を返す。
- CloudFormation contract test が schedule名、rate、target queue、payload、role permission を検証する。
- README に低頻度 Scheduler の運用方針を追記する。
- 変更範囲に見合う検証と `npm run verify` が成功する。

## 完了確認

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/18
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/18#issuecomment-4569994938
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/18#issuecomment-4569996792
- 作業レポート: `reports/working/20260529-1130-eventbridge-scheduler-low-frequency-report.md`
- 検証: `git diff --check`、`python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`、`PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py tests/test_core_pipeline.py`、`npm test`、`npm run verify`
- 未実施: 実 AWS 環境への deploy と EventBridge Scheduler 実発火確認
