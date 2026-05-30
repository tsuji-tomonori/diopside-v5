# Worker batch v0.4 coverage audit

## 位置づけ

`docs/design/diopside_basic_design_v0.4.md` の 9.6 / 9.8 を正本とし、現 worker 実装は移行中の実装候補として扱う。現状は `apps/workers/static-exporter/src/static_exporter/pipeline.py` に metadata / chat / normalize / aggregate / maintenance 系の複数責務が統合され、`apps/workers/static-exporter/src/static_exporter/handler.py` が static export を担う。v0.4 が求める worker 分割、batch ごとの handler / job_type / queue / idempotency test は一部のみ満たすため、worker 物理分割は差分ありとして後続管理する。

## BATCH-001〜020 対応表

| ID | v0.4 batch | 現 job_type / handler | queue / trigger | test evidence | 状態 | 備考 |
|---|---|---|---|---|---|---|
| BATCH-001 | 定期メタデータ同期ディスパッチ | `metadata_sync` message を Scheduler/API が作成 | `MetadataQueue` / 管理 API | `tests/test_cloudformation_contract.py`, `tests/test_api_handler.py` | 部分実装 | 専用 dispatcher Lambda ではなく Scheduler/API 直投入 |
| BATCH-002 | チャンネル情報取得 | `metadata_sync` | `DIOPSIDE_METADATA_QUEUE_URL` | `tests/test_core_pipeline.py` | 部分実装 | channel resource 専用 branch は未分離 |
| BATCH-003 | uploads playlist差分取得 | `metadata_sync` | `DIOPSIDE_METADATA_QUEUE_URL` | `tests/test_core_pipeline.py` | 実装済 | page token cursor と次 page 再投入を検証 |
| BATCH-004 | 動画詳細取得 | `metadata_sync` | `DIOPSIDE_METADATA_QUEUE_URL` | `tests/test_core_pipeline.py` | 部分実装 | 状態変化 event item は v0.4 未整合 |
| BATCH-005 | ライブ状態監視 | `live_status_scan` | `DIOPSIDE_METADATA_QUEUE_URL` | `tests/test_core_pipeline.py`, `tests/test_cloudformation_contract.py` | 部分実装 | chat collect / notification_plan / archive_finalize の後続投入に対応 |
| BATCH-006 | 配信予定通知生成 | `notification_plan` | `DIOPSIDE_AGGREGATE_QUEUE_URL` | `tests/test_core_pipeline.py`, `tests/test_worker_batch_coverage_contract.py` | 部分実装 | NotificationPlan item 作成に対応。外部通知 delivery / DLQ は未実装 |
| BATCH-007 | 公式Live Chat取得 | `chat_collect` mode=`live` | `DIOPSIDE_CHAT_QUEUE_URL` | `tests/test_core_pipeline.py` | 部分実装 | Live Chat page 取得と requeue はあるが専用 worker 分離なし |
| BATCH-008 | リプレイチャット初期化 | `chat_collect` mode=`replay` | `DIOPSIDE_CHAT_QUEUE_URL` | `tests/test_core_pipeline.py` | 部分実装 | initial data 解析はあるが初期化 worker と page collector は未分離 |
| BATCH-009 | リプレイチャットページ取得 | `chat_collect` mode=`replay` | `DIOPSIDE_CHAT_QUEUE_URL` | `tests/test_core_pipeline.py` | 部分実装 | continuation 自己再投入の専用 contract は不足 |
| BATCH-010 | チャット正規化 | `chat_normalize` | `DIOPSIDE_NORMALIZE_QUEUE_URL` | `tests/test_core_pipeline.py` | 実装済 | streaming normalize と summary 更新を検証 |
| BATCH-011 | チャット集計 | `chat_normalize` 内 aggregate | `DIOPSIDE_NORMALIZE_QUEUE_URL` | `tests/test_core_pipeline.py` | 部分実装 | aggregate worker は未分離 |
| BATCH-012 | ワードクラウド生成 | `rebuild_artifacts` / `static_export` | `DIOPSIDE_AGGREGATE_QUEUE_URL` | `tests/test_core_pipeline.py`, `tests/test_static_exporter.py` | 部分実装 | PNG/JSON と互換 SVG を出力。専用 wordcloud worker 分割は未実装 |
| BATCH-013 | タイムスタンプ候補生成 | `rebuild_artifacts` | `DIOPSIDE_AGGREGATE_QUEUE_URL` | `tests/test_core_pipeline.py`, `tests/test_static_exporter.py` | 部分実装 | chapters_suggestion.md は未実装 |
| BATCH-014 | ファイル出力サービス | `file_output`, `static_export` | `DIOPSIDE_AGGREGATE_QUEUE_URL`, `DIOPSIDE_STATIC_EXPORT_QUEUE_URL` | `tests/test_core_pipeline.py`, `tests/test_static_exporter.py`, `tests/test_worker_batch_coverage_contract.py` | 部分実装 | `file_output` job は public/private artifact body と `Artifact` item を記録。物理的な専用 worker 分割は未実装 |
| BATCH-015 | 静的JSON export | `static_export` / `static_exporter.handler` | `DIOPSIDE_STATIC_EXPORT_QUEUE_URL` | `tests/test_static_exporter.py`, `tools/check-public-contract.mjs` | 実装済 | v0.4 alias と versioned manifest を検証 |
| BATCH-016 | quota使用量ロールアップ | `quota_rollup` | `DIOPSIDE_AGGREGATE_QUEUE_URL` | `tests/test_core_pipeline.py`, `tests/test_repository_schema_contract.py` | 部分実装 | call record から v0.4 key shape の daily method summary item を保存。quota threshold warning event は未実装 |
| BATCH-017 | アーカイブ確定処理 | `archive_finalize` | `DIOPSIDE_AGGREGATE_QUEUE_URL` | `tests/test_core_pipeline.py`, `tests/test_worker_batch_coverage_contract.py` | 部分実装 | live ended 検知から replay collect / static export を後続投入。遅延 Scheduler と NotificationPlan 連携は未実装 |
| BATCH-018 | 失敗ジョブ再投入/Redrive | `retry_job` | target job queue | `tests/test_core_pipeline.py`, `tests/test_api_handler.py` | 部分実装 | DLQ redrive report は手順中心 |
| BATCH-019 | 古いraw/中間成果物クリーンアップ | `cleanup` | `DIOPSIDE_AGGREGATE_QUEUE_URL` | `tests/test_core_pipeline.py`, `tests/test_cloudformation_contract.py` | 部分実装 | 現状は dry-run report のみで削除しない |
| BATCH-020 | 管理手動ジョブディスパッチ | admin job API | 各 queue | `tests/test_api_handler.py`, `tests/test_core_pipeline.py`, `tools/run-local-e2e.mjs` | 部分実装 | 管理 API と worker 後続投入は v0.4 `JobMessage` field を送信。EventBridge Scheduler template と GitHub Actions dispatch は未整合 |

## 現 worker contract

- `static_exporter.pipeline` が dispatch する job_type は `metadata_sync`、`live_status_scan`、`chat_collect`、`chat_normalize`、`rebuild_artifacts`、`file_output`、`archive_finalize`、`notification_plan`、`retry_job`、`cancel_job`、`quota_rollup`、`cleanup`。
- `static_export` は `static_exporter.handler` が担当する。
- queue env mapping は `metadata_sync` / `live_status_scan` / `retry_job` / `cancel_job` を `DIOPSIDE_METADATA_QUEUE_URL`、`chat_collect` を `DIOPSIDE_CHAT_QUEUE_URL`、`chat_normalize` を `DIOPSIDE_NORMALIZE_QUEUE_URL`、`rebuild_artifacts` / `file_output` / `archive_finalize` / `notification_plan` / `quota_rollup` / `cleanup` を `DIOPSIDE_AGGREGATE_QUEUE_URL`、`static_export` を `DIOPSIDE_STATIC_EXPORT_QUEUE_URL` に割り当てる。
- 管理 API と worker の後続投入は v0.4 `JobMessage` field として `job_id`、`job_type`、`idempotency_key`、`requested_by`、`attempt`、`trace_id`、`payload` を送る。`dispatch_job` は既存外部 producer 互換のため旧 `input` field も受け付ける。
- `file_output` は BATCH-014 の worker job として、入力 payload 由来の body / json_body / body_base64 を public/private artifact key へ出力し、`Artifact` item に `artifact_version`、`content_hash`、`byte_size`、`generated_at` を保存する。
- `notification_plan` は `before_30min`、`at_start`、`archive_available` の `NotificationPlan` item を v0.4 key shape で冪等作成する。
- `quota_rollup` は `QuotaUsage` call record を日別・method別に集計し、`pk=QUOTA#{yyyyMMdd}` / `sk=METHOD#{method}` の daily summary item を upsert する。
- `cleanup` は削除を実行せず、常に dry-run report を返す。
- `retry_job` は対象 job の job_type から queue env を引き、`retry_requested` event を残して再投入する。

## 後続修正方針

1. BATCH-006 の外部通知 delivery / DLQ / sent/skipped/failed 更新を実装する。
2. `archive_finalize` の遅延 Scheduler 連携を実装し、archive_available の通知時刻を運用要件に合わせる。
3. BATCH-011 / 012 / 013 を aggregate 統合処理から分離し、wordcloud / timestamp の job_type と queue contract を追加する。BATCH-014 は `file_output` job_type を追加済みだが、物理 worker 分割は後続で行う。
4. BATCH-008 / 009 は replay 初期化と page collector を分け、continuation の自己再投入 contract を明確にする。
5. BATCH-016 は quota threshold warning event、上限接近時の通知、管理 UI での summary 表示へ接続する。
6. EventBridge Scheduler template と GitHub Actions workflow_dispatch 由来の message fields を v0.4 `JobMessage` 共通 schema へ統一する。
