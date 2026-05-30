# ChatPageManifest v0.4 key 対応 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と `.workspace/` の設計書に沿って v0.4 設計準拠を進める。
- main を pull してから worktree / task / PR flow で作業する。

## 要件整理

- raw chat page manifest の新規保存 key を `VID#{video_id}` / `CHAT#PAGE#{source}#{seq}` にする。
- `chat_collect` は repository method 経由で page manifest を保存する。
- 既存 `ChatMessageChunkManifest` / `VIDEO#{video_id}` / `CHAT#RAW#...` は読み取り fallback として維持する。
- README と schema audit を実装済み範囲に同期する。

## 検討・判断

- `ChatPageManifest` は v0.4 field の `raw_s3_uri`、`item_count`、`checksum` を持たせた。
- 既存 `chat_normalize` が `s3_uri`、`message_count`、`sha256` を読むため、新 item に互換 alias を残した。
- `list_chat_chunks` は新 `ChatPageManifest` を優先し、新 item が存在しない動画では旧 chunk manifest を fallback する。
- TTL 運用、既存 data backfill、replay continuation 巡回取得は後続範囲として残した。

## 実施作業

- `chat_page_manifest_item`、`put_chat_page_manifest` を追加した。
- `list_chat_chunks` を `ChatPageManifest` 優先 + 旧 `ChatMessageChunkManifest` fallback に更新した。
- `chat_collect` の raw page manifest 保存を direct `put_item` から `put_chat_page_manifest` に変更した。
- repository schema contract と chat collect / normalize pipeline test に v0.4 key / fallback assertion を追加した。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の `ChatPageManifest` 記述を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_repository_schema_contract.py`
- `tests/test_core_pipeline.py`
- `README.md`
- `docs/design/dynamodb-schema-audit.md`
- `tasks/do/20260530-1510-chat-page-manifest-v04-key.md`

## 検証

- `git diff --check` pass
- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py` pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py` pass: 25 passed
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_static_exporter.py` pass: 50 passed
- `node tools/check-docs-consistency.mjs` pass
- `npm run verify` pass: 126 tests passed, build/package/e2e local passed

## Fit 評価

- 新規保存は v0.4 key に寄せ、旧 raw chunk manifest は fallback で維持したため受け入れ条件に合致。
- chat 本文を DDB に保存せず、raw body は S3 に置き、DDB には manifest metadata のみを保存している。
- docs は実装済み範囲と未対応範囲を分けて記載した。

## 未対応・制約・リスク

- 既存 DynamoDB data の backfill は未実施。
- raw page TTL の DynamoDB 設定と削除運用は未実施。
- live/replay collection state machine との完全接続は未実施。
- 複数 replay continuation page の巡回取得は未実施。
