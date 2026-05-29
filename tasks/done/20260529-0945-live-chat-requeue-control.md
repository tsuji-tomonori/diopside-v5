# live chat collect 再投入制御

状態: done
タスク種別: 機能追加

## 背景

`.workspace/plan-20260529.txt` の Phase 1 では、P1-07 として live chat collect の再投入制御が必要とされている。現状の `chat_collect` は `nextPageToken` があれば再投入するが、`offlineAt`、`rateLimitExceeded`、停止理由、manifest の `next_poll` 表現が弱く、運用判断に必要な状態が不足している。

## 目的

`liveChatMessages.list` の `nextPageToken`、`pollingIntervalMillis`、`offlineAt`、`rateLimitExceeded` に応じて、SQS 再投入・停止・失敗イベント相当の判断を worker 結果と raw chunk manifest に残す。

## スコープ

- 対象: `apps/workers/static-exporter/src/static_exporter/pipeline.py`、`tests/test_core_pipeline.py`、`README.md`、作業レポート。
- 対象 P1: P1-07。
- 対象外: 実 YouTube API 呼び出し、実 AWS deploy、replay collector 実データ検証、normalized schema 固定。

## 実施計画

1. live chat response から `rateLimitExceeded` を検出し、retryable failure として扱う。
2. `offlineAt` がある場合は再投入せず、停止理由を `next_poll` に残す。
3. `nextPageToken` があり rate limit/offline でない場合だけ SQS delay 再投入する。
4. `pollingIntervalMillis` から delay seconds を計算し、SQS limit 900 秒で clamp する。
5. raw chunk manifest と job result に `next_poll.action`、`stop_reason`、`requeue_delay_seconds` を残す。
6. unit test と README を更新する。

## ドキュメント保守計画

- README の live chat collect / quota 節約方針に、再投入・停止・rate limit の扱いを追記する。

## 受け入れ条件

- [x] `nextPageToken` があり、`rateLimitExceeded` と `offlineAt` がない場合だけ `chat_collect` が SQS delay 再投入する。
  - 根拠: `tests/test_core_pipeline.py::test_live_chat_collect_requeues_with_clamped_delay`。
- [x] `pollingIntervalMillis` は秒に変換され、SQS `DelaySeconds` は 900 秒を上限に clamp される。
  - 根拠: `tests/test_core_pipeline.py::test_live_chat_collect_requeues_with_clamped_delay`。
- [x] `offlineAt` がある場合は再投入せず、`next_poll.action` が停止を示す。
  - 根拠: `tests/test_core_pipeline.py::test_live_chat_collect_stops_when_offline`。
- [x] `rateLimitExceeded` がある場合は再投入せず、`next_poll.action` と `stop_reason` が rate limit を示す。
  - 根拠: `tests/test_core_pipeline.py::test_live_chat_collect_does_not_requeue_on_rate_limit`。
- [x] raw chunk manifest に `next_poll` と message count / raw JSONL URI が保存される。
  - 根拠: `tests/test_core_pipeline.py::test_live_chat_collect_requeues_with_clamped_delay`。
- [x] README に live chat collect 再投入制御が反映されている。
- [x] 変更範囲に応じた tests と `npm run verify` が成功する。

## 検証計画

- `git diff --check`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`: 初回 fail -> mock response 時に `YouTubeClient()` を生成しないよう修正後 pass
- `npm test`: pass
- `npm run verify`: pass

## PRレビュー観点

- Lambda 内で長時間 sleep していないこと。
- rate limit 時に無限再投入しないこと。
- offlineAt 時に完了/停止を表現できること。
- stacked branch である制約を PR 本文に明記すること。

## リスク

- この branch は PR #5 を土台にした stacked worktree であり、PR #3/#4/#5 が merge されるまで main 向け差分には前段 PR の変更も含まれる。
- 実 YouTube API 呼び出しと実 SQS 接続は行わず、mock/local artifact で検証する。
