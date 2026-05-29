# quota usageの可視化 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づき、main を pull してから継続作業する。
- P1-15「quota usageの可視化」として、YouTube API method、units、video_count、channel_id、job_id を `QuotaUsage` に記録し、管理UI/APIで確認できるようにする。

## 要件整理

- YouTube API 呼び出し時に quota usage を DynamoDB / repository へ記録する。
- 管理 API の `GET /api/admin/quota-usage` で method、units、video_count、channel_id、job_id を top-level field として返す。
- 管理 UI の quota 表示で同じ field を確認できる。
- 既存の post-deploy smoke / local e2e でも quota usage schema を確認する。

## 検討・判断

- `QuotaUsage.details` だけに埋めると管理 UI/API の contract が曖昧になるため、表示・検証対象 field は item の top-level に正規化した。
- `dispatch_job` で worker の入力 params に `job_id` を付与し、metadata sync、live status scan、live chat collect の quota record へ渡すようにした。
- `live_status_scan` は YouTube `videos.list` で候補動画を refresh した場合に quota usage を記録する。50件 chunk 単位で `units=1` として記録する。
- `chat_collect` は real `liveChatMessages.list` 呼び出し時のみ記録し、fixture response を渡す test/dev 経路では不要な quota 記録をしない。

## 実施作業

- `Repository.record_quota_usage` に `channel_id`、`video_count`、`job_id` を追加し、top-level と details の両方へ保存。
- `metadata_sync` の `playlistItems.list` / `videos.list` に job_id と video_count を記録。
- `live_status_scan` で `videos.list` refresh と quota usage 記録を追加。
- `chat_collect` の `liveChatMessages.list` 呼び出しに quota usage 記録を追加。
- 管理 API の quota usage 応答で過去 item の details fallback も含め top-level field を返すよう更新。
- 管理 UI の quota 表示を method / units / videos / channel / job へ拡張。
- local e2e と post-deploy smoke で quota usage item field を検証。
- README の quota usage 説明を更新。

## 成果物

- quota usage 記録と管理 UI/API 表示の強化。
- 作業 task: `tasks/do/20260529-1055-quota-usage-visibility.md`

## 検証

- `git diff --check`: 成功
- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py apps/api/src/diopside_api/handler.py`: 成功
- `node --check tools/run-local-e2e.mjs`: 成功
- `node --check tools/run-post-deploy-smoke.mjs`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_api_handler.py`: 31 passed
- `npm test`: 40 passed
- `npm run verify`: 成功

## fit 評価

- P1-15 の method、units、video_count、channel_id、job_id の記録と管理 API/UI 表示は実装済み。
- metadata sync / live status scan / live chat collect の YouTube API 呼び出しを quota usage 記録対象にした。
- post-deploy smoke は実行時に quota usage schema を検証する。

## 未対応・制約・リスク

- 実 CloudFront / AWS 環境に対する `npm run smoke:post-deploy` は、対象 URL と認証情報が必要なため未実行。
- YouTube Data API の公式 quota unit は method ごとに固定値として扱っている。将来 `search.list` など unit が大きい API を追加する場合は method 別 unit table を追加する。
