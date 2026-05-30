# ChatManifest v0.4 key 対応

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、DDB item schema の差分解消が残っている。`docs/design/dynamodb-schema-audit.md` では `ChatManifest` が `VID#{video_id}` / `CHAT#MANIFEST` として設計されている一方、現行 `chat_normalize` は `VIDEO#{video_id}` / `CHAT#MANIFEST` へ直接 `put_item` している。

## 目的

正規化チャット manifest の新規保存 key を v0.4 の `VID#{video_id}` / `CHAT#MANIFEST` に寄せ、既存 `VIDEO#...` manifest の読み取り fallback を維持する。

## タスク種別

機能追加

## スコープ

- `apps/shared/src/diopside_core/repository.py` の `ChatManifest` writer/get。
- `apps/workers/static-exporter/src/static_exporter/pipeline.py` の `chat_normalize` manifest 保存。
- `tests/test_repository_schema_contract.py` と既存 chat normalize 経路の contract。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の ChatManifest 形状記述。
- 作業レポート、PR コメント、task done 更新。

## スコープ外

- 既存 DynamoDB data の backfill。
- ChatPageManifest への raw page manifest 名変更。
- live/replay collection state の完全運用接続。

## 実施計画

1. 現行 `chat_normalize` の `ChatManifest` 保存と v0.4 schema を確認する。
2. `chat_manifest_item` helper と `put_chat_manifest` / `get_chat_manifest` を repository に追加する。
3. `chat_normalize` が repository method 経由で `VID#{video_id}` / `CHAT#MANIFEST` に保存するようにする。
4. `get_chat_manifest` は新 key を優先し、旧 `VIDEO#...` / `CHAT#MANIFEST` を fallback する。
5. schema contract test と audit / README を更新する。
6. targeted test、docs consistency、diff check、全体 verify を実行する。

## ドキュメントメンテナンス方針

`README.md` の item schema 表と `docs/design/dynamodb-schema-audit.md` の `ChatManifest` 行を更新する。設計書本体は既に v0.4 形状を記載しているため、audit 側を実装済みに寄せる。

## 受け入れ条件

- [ ] `put_chat_manifest` が `pk=VID#{video_id}` / `sk=CHAT#MANIFEST` の `ChatManifest` item を保存する。
- [ ] `ChatManifest` item が `video_id`、`normalized_s3_uri`、`message_count`、`live_collection_state`、`replay_collection_state`、`normalization_state` を持つ。
- [ ] `get_chat_manifest` が新 key を優先し、旧 `VIDEO#...` / `CHAT#MANIFEST` も fallback で扱える。
- [ ] `chat_normalize` が v0.4 key の `ChatManifest` を保存し、既存 chat normalize tests が通る。
- [ ] `README.md` と `docs/design/dynamodb-schema-audit.md` が実装済み形状に同期している。
- [ ] 選定した検証コマンドが pass し、未実施の検証がある場合は理由を記録する。
- [ ] PR に受け入れ条件確認コメントとセルフレビューコメントを日本語で追加する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_static_exporter.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- v0.4 key へ新規保存しつつ、旧 manifest の読み取り互換を壊していないこと。
- chat 本文を DynamoDB に保存していないこと。
- ChatPageManifest 変更や live/replay state 完全接続を実施済みと誤記していないこと。

## リスク

- 既存 DynamoDB data への backfill は未実施。
- live/replay collection state の詳細更新は現時点では default read model 値であり、完全な state machine 接続は後続。

## 状態

in_progress
