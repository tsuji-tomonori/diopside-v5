# ChannelSyncCursor v0.4 key 対応 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と `.workspace/` の設計書に沿って v0.4 設計準拠を進める。
- main を pull してから worktree / task / PR flow で作業する。

## 要件整理

- metadata sync cursor の新規保存 key を `CH#{channel_id}` / `CURSOR#uploads` にする。
- `metadata_sync` は repository method 経由で cursor を保存・取得する。
- 既存 `ChannelCursor` / `CHANNEL#{channel_id}` / `CURSOR#metadata` は読み取り fallback として維持する。
- README と schema audit を実装済み範囲に同期する。

## 検討・判断

- `ChannelSyncCursor` は v0.4 field の `uploads_playlist_id`、last seen video、`next_page_token_hash` を持たせた。
- 現行再開処理互換のため、`next_page_token` 本体も保持した。hash-only 化は後続範囲として残した。
- `get_channel_sync_cursor` は新 key を優先し、旧 `ChannelCursor` を fallback する。

## 実施作業

- `channel_sync_cursor_item`、`put_channel_sync_cursor`、`get_channel_sync_cursor` を追加した。
- `metadata_sync` の cursor 保存・取得を repository method 経由に変更した。
- repository schema contract と metadata sync pipeline test に v0.4 key / fallback assertion を追加した。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の `ChannelSyncCursor` 記述を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_repository_schema_contract.py`
- `tests/test_core_pipeline.py`
- `README.md`
- `docs/design/dynamodb-schema-audit.md`
- `tasks/do/20260530-1537-channel-sync-cursor-v04-key.md`

## 検証

- `git diff --check` pass
- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py` pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py` pass: 27 passed
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py` pass: 43 passed
- `node tools/check-docs-consistency.mjs` pass
- `npm run verify` pass: 128 tests passed, build/package/e2e local passed

## Fit 評価

- 新規保存は v0.4 key に寄せ、旧 cursor は fallback で維持したため受け入れ条件に合致。
- YouTube raw response 本文は S3 に置き、DDB には cursor metadata のみを保存している。
- docs は実装済み範囲と未対応範囲を分けて記載した。

## 未対応・制約・リスク

- 既存 DynamoDB data の backfill は未実施。
- page token の hash-only 化は未実施。
- metadata sync worker の物理分割は未実施。
