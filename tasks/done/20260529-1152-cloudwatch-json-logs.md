# CloudWatch JSONログ

状態: done

## 背景

`.workspace/plan-20260529.txt` の P2-06 に従い、API/worker が CloudWatch で検索しやすい JSON log を出力するようにする。

## 目的

API と worker の実行結果を、`trace_id`、`job_id`、`video_id`、`result`、`duration_ms`、`error` を含む JSON log として記録し、障害調査や post-deploy smoke の追跡性を上げる。

## タスク種別

機能追加

## スコープ

- API Lambda handler の request 単位 JSON log
- worker pipeline の job 単位 JSON log
- 既存 error response / JobEvent の挙動を壊さない範囲の logging helper
- README への運用ログ方針追記
- unit test による JSON log contract 確認

## 計画

1. API handler と worker pipeline の現行 logging / error handling を確認する。
2. 共通または各 module の最小 helper で JSON log を出力する。
3. API success/error と worker success/error の contract test を追加する。
4. README に CloudWatch JSON log の field と調査観点を追記する。
5. 検証、作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

運用 observability の挙動が変わるため、README の運用 section に JSON log fields と trace/job/video の追跡方法を追記する。

## 受け入れ条件

- API が request 完了時に JSON log を出力し、`trace_id`、`result`、`duration_ms` を含む。
- API error 時の JSON log が `error` と HTTP status を含み、既存 ErrorResponse の `trace_id` と対応する。
- worker が job 完了時に JSON log を出力し、`job_id`、`job_type`、`result`、`duration_ms` を含む。
- worker error 時の JSON log が `error`、`job_id`、`job_type` を含み、既存 failed debug artifact / JobEvent を壊さない。
- `video_id` が payload/input/result から分かる場合、API/worker log に含まれる。
- README に CloudWatch JSON log の field と調査観点が記載されている。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- API handler / worker pipeline targeted pytest
- `npm test`
- 必要に応じて `npm run verify`

## PRレビュー観点

- log が JSON 1 行で CloudWatch Logs Insights から検索しやすいこと。
- 例外時に既存の error response、debug artifact、JobEvent が変わらないこと。
- secret/token/API key を log に出していないこと。

## リスク

- stdout logging は CloudWatch へ送られるため、payload 全体や認証情報は出さない。
- 実 CloudWatch Logs Insights での検索は実 AWS deploy 後の確認事項として残る。

## 完了確認

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/20
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/20#issuecomment-4570047834
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/20#issuecomment-4570049285
- 作業レポート: `reports/working/20260529-1152-cloudwatch-json-logs-report.md`
- 検証: `git diff --check`、`python3 -m py_compile apps/api/src/diopside_api/handler.py apps/workers/static-exporter/src/static_exporter/pipeline.py`、targeted pytest、`npm test`、`npm run verify`
- 未実施: 実 AWS CloudWatch Logs への出力と Logs Insights での検索
