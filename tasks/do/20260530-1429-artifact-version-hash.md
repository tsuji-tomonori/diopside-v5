# Artifact version/hash contract 対応

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、DDB item schema の差分解消が残っている。`docs/design/dynamodb-schema-audit.md` では `Artifact` が v0.4 の `VID#{video_id}` / `ARTIFACT#{artifact_type}#{artifact_version}` と異なり、現行 `put_artifact` は `VIDEO#{video_id}` / `ARTIFACT#{artifact_type}` で `artifact_version` と `content_hash` required 化が未整合と記録されている。

## 目的

`Artifact` item を v0.4 の versioned key と required metadata に寄せ、既存の artifact lookup/list 互換を維持する。

## タスク種別

機能追加

## スコープ

- `apps/shared/src/diopside_core/repository.py` の `Artifact` item writer/list/get。
- `tests/test_repository_schema_contract.py` と既存 pipeline tests の artifact contract。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の Artifact 形状記述。
- 作業レポート、PR コメント、task done 更新。

## スコープ外

- 既存 DynamoDB data の backfill。
- public/private artifact body の再生成。
- artifact payload schema の全面的な v0.4 schema 化。

## 実施計画

1. 現行 `put_artifact` / `list_artifacts` / `get_artifact_by_id` と worker の `file_output` 呼び出しを確認する。
2. `artifact_version` default と `content_hash` default を持つ `Artifact` item helper を追加する。
3. 新規保存 key を `VID#{video_id}` / `ARTIFACT#{artifact_type}#{artifact_version}` に寄せ、旧 `VIDEO#...` item の読み取り fallback を残す。
4. schema contract test と audit / README を更新する。
5. targeted test、docs consistency、diff check、全体 verify を実行する。

## ドキュメントメンテナンス方針

`README.md` の item schema 表と `docs/design/dynamodb-schema-audit.md` の `Artifact` 行を更新する。設計書本体は既に v0.4 形状を記載しているため、audit 側を実装済みに寄せる。

## 受け入れ条件

- [ ] `put_artifact` が `pk=VID#{video_id}` / `sk=ARTIFACT#{artifact_type}#{artifact_version}` の `Artifact` item を保存する。
- [ ] `Artifact` item が `artifact_version` と `content_hash` を必ず持つ。
- [ ] `list_artifacts` / `get_artifact_by_id` が新 shape を返し、旧 `VIDEO#...` artifact も fallback で扱える。
- [ ] 既存 `file_output` の artifact 保存・参照テストが通る。
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

- `Artifact` の新規保存 key が versioned になっていること。
- 旧 artifact item の lookup/list fallback を残していること。
- `content_hash` は未指定時も deterministic に付与されるが、実 body hash ではない場合があることを過剰に主張していないこと。

## リスク

- 既存 DynamoDB artifact item の backfill は未実施。
- `content_hash` 未指定時の fallback hash は manifest metadata 由来であり、artifact body そのものの hash ではない。

## 状態

in_progress
