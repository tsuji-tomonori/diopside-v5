# ChatAggregate v0.4 key 対応

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、DDB item schema の差分解消が残っている。`docs/design/dynamodb-schema-audit.md` では `ChatAggregate` が `VID#{video_id}` / `CHAT#AGG#v1` として設計されている一方、現行 `put_chat_aggregate` は `VIDEO#{video_id}` / `CHAT#AGGREGATE` へ保存している。

## 目的

`ChatAggregate` の新規保存 key を v0.4 の `VID#{video_id}` / `CHAT#AGG#v1` に寄せ、既存 `VIDEO#...` aggregate の読み取り fallback を維持する。

## タスク種別

機能追加

## スコープ

- `apps/shared/src/diopside_core/repository.py` の `ChatAggregate` writer/get。
- `tests/test_repository_schema_contract.py` と既存 chat aggregate 経路の contract。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の ChatAggregate 形状記述。
- 作業レポート、PR コメント、task done 更新。

## スコープ外

- 既存 DynamoDB data の backfill。
- `source_normalized_s3_uri` / `heatmap_s3_uri` の required 化。
- chat aggregate payload schema の全面固定。

## 実施計画

1. 現行 `put_chat_aggregate` / `get_chat_aggregate` と worker/static export の利用箇所を確認する。
2. `chat_aggregate_item` helper を追加し、新規保存 key を `VID#{video_id}` / `CHAT#AGG#v1` にする。
3. `get_chat_aggregate` は新 key を優先し、旧 `VIDEO#...` / `CHAT#AGGREGATE` を fallback する。
4. schema contract test と audit / README を更新する。
5. targeted test、docs consistency、diff check、全体 verify を実行する。

## ドキュメントメンテナンス方針

`README.md` の item schema 表と `docs/design/dynamodb-schema-audit.md` の `ChatAggregate` 行を更新する。設計書本体は既に v0.4 形状を記載しているため、audit 側を実装済みに寄せる。

## 受け入れ条件

- [ ] `put_chat_aggregate` が `pk=VID#{video_id}` / `sk=CHAT#AGG#v1` の `ChatAggregate` item を保存する。
- [ ] `ChatAggregate` item が `video_id`、`aggregate_version`、`message_count`、`computed_at` を持つ。
- [ ] `get_chat_aggregate` が新 key を優先し、旧 `VIDEO#...` / `CHAT#AGGREGATE` も fallback で扱える。
- [ ] 既存 chat aggregate / static export 経路のテストが通る。
- [ ] `README.md` と `docs/design/dynamodb-schema-audit.md` が実装済み形状に同期している。
- [ ] 選定した検証コマンドが pass し、未実施の検証がある場合は理由を記録する。
- [ ] PR に受け入れ条件確認コメントとセルフレビューコメントを日本語で追加する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_static_exporter.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- v0.4 key へ新規保存しつつ、旧 aggregate の読み取り互換を壊していないこと。
- required URI field の完全固定を今回実施済みと誤記していないこと。
- chat aggregate を使う wordcloud/static export 経路が壊れていないこと。

## リスク

- 既存 DynamoDB data への backfill は未実施。
- `source_normalized_s3_uri` / `heatmap_s3_uri` の required 化と payload schema 完全固定は後続。

## 状態

in_progress
