# ChatManifest v0.4 key 対応 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と `.workspace/` の設計書に沿って v0.4 設計準拠を進める。
- main を pull してから worktree / task / PR flow で作業する。

## 要件整理

- `ChatManifest` の新規保存 key を `VID#{video_id}` / `CHAT#MANIFEST` にする。
- `chat_normalize` は repository method 経由で manifest を保存する。
- 既存 `VIDEO#{video_id}` / `CHAT#MANIFEST` は読み取り fallback として維持する。
- README と schema audit を実装済み範囲に同期する。

## 検討・判断

- `ChatManifest` item helper を repository 側へ追加し、DynamoDB / Memory repository の保存形状を同一化した。
- `normalized_uri` は旧 field として入力互換だけ維持し、新規 item では `normalized_s3_uri` に正規化する。
- live/replay collection state と normalization state は manifest 生成時点で default を付与するが、完全な state machine 接続や既存 data backfill は後続範囲として残した。

## 実施作業

- `chat_manifest_item`、`put_chat_manifest`、`get_chat_manifest` を追加した。
- `chat_normalize` の manifest 保存を direct `put_item` から `put_chat_manifest` に変更した。
- repository schema contract と chat normalize pipeline test に v0.4 key / fallback assertion を追加した。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の `ChatManifest` 記述を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_repository_schema_contract.py`
- `tests/test_core_pipeline.py`
- `README.md`
- `docs/design/dynamodb-schema-audit.md`
- `tasks/do/20260530-1458-chat-manifest-v04-key.md`

## 検証

- `git diff --check` pass
- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py` pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py` pass: 24 passed
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_static_exporter.py` pass: 50 passed
- `node tools/check-docs-consistency.mjs` pass
- `npm run verify` pass: 125 tests passed, build/package/e2e local passed

## Fit 評価

- 新規保存は v0.4 key に寄せ、旧 key は fallback で維持したため受け入れ条件に合致。
- chat 本文を DDB に保存せず、manifest の保存先と集計のみを扱っている。
- docs は実装済み範囲と未対応範囲を分けて記載した。

## 未対応・制約・リスク

- 既存 DynamoDB data の backfill は未実施。
- live/replay collection state の完全な state machine 接続は未実施。
- ChatPageManifest への raw page manifest 名称/key 分離は未実施。
