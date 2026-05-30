# ChannelSyncCursor v0.4 key 対応

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、DDB item schema の差分解消が残っている。`docs/design/dynamodb-schema-audit.md` では metadata sync cursor が `ChannelSyncCursor`、`CH#{channel_id}` / `CURSOR#uploads` として設計されている一方、現行 `metadata_sync` は `ChannelCursor`、`CHANNEL#{channel_id}` / `CURSOR#metadata` へ直接 `put_item` している。

## 目的

uploads playlist 差分 cursor の新規保存 key を v0.4 の `CH#{channel_id}` / `CURSOR#uploads` に寄せ、既存 `ChannelCursor` / `CHANNEL#...` の読み取り fallback を維持する。

## タスク種別

機能追加

## スコープ

- `apps/shared/src/diopside_core/repository.py` の `ChannelSyncCursor` writer/get。
- `apps/workers/static-exporter/src/static_exporter/pipeline.py` の `metadata_sync` cursor 保存・取得。
- `tests/test_core_pipeline.py` と `tests/test_repository_schema_contract.py` の contract。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の cursor 形状記述。
- 作業レポート、PR コメント、task done 更新。

## スコープ外

- 既存 DynamoDB data の backfill。
- page token の完全 hash-only 化。
- metadata sync の worker 物理分割。

## 受け入れ条件

- [x] `put_channel_sync_cursor` が `pk=CH#{channel_id}` / `sk=CURSOR#uploads` の `ChannelSyncCursor` item を保存する。
- [x] `ChannelSyncCursor` item が `channel_id`、`uploads_playlist_id`、`last_seen_video_id`、`next_page_token`、`raw_playlist_uri`、`raw_videos_uri`、`saved_count` を持つ。
- [x] `get_channel_sync_cursor` が新 key を優先し、旧 `CHANNEL#...` / `CURSOR#metadata` も fallback で扱える。
- [x] `metadata_sync` が v0.4 key の `ChannelSyncCursor` を保存し、既存 metadata sync tests が通る。
- [x] `README.md` と `docs/design/dynamodb-schema-audit.md` が実装済み形状に同期している。
- [x] 選定した検証コマンドが pass し、未実施の検証がある場合は理由を記録する。
- [x] PR に受け入れ条件確認コメントとセルフレビューコメントを日本語で追加する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## リスク

- 既存 DynamoDB data への backfill は未実施。
- `next_page_token` は現行の再開処理互換のため保持し、hash-only 化は後続。

## 実施結果

- `channel_sync_cursor_item`、`put_channel_sync_cursor`、`get_channel_sync_cursor` を追加し、新規保存を `CH#{channel_id}` / `CURSOR#uploads` に変更した。
- `metadata_sync` の cursor 保存と取得を repository method 経由に変更した。
- 旧 `ChannelCursor` / `CHANNEL#{channel_id}` / `CURSOR#metadata` は fallback として維持した。
- README と `docs/design/dynamodb-schema-audit.md` を実装済み形状に同期した。
- 作業レポートを `reports/working/20260530-1537-channel-sync-cursor-v04-key.md` に作成した。

## 検証結果

- `git diff --check`: pass
- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py`: pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`: 27 passed
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`: 43 passed
- `node tools/check-docs-consistency.mjs`: pass
- `npm run verify`: 128 tests passed + build/package/local e2e passed

## PR コメント

- 受け入れ条件確認: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581973871
- セルフレビュー: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581973855

## 状態

done
