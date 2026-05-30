# TagSummary item

## 背景

`.workspace/plan-20260530.txt` は v0.4 DDB item schema への準拠を検収基準に戻す方針を示している。
v0.4 の `TagSummary` は `pk=TAG#{tag_id}`, `sk=META` でタグ一覧・表示名・件数・カテゴリを保持する read model だが、現状は `list_tags` が動画の `tags` から動的生成しているだけで、DDB item が保存されていない。

## 目的

動画保存・タグ補正時に `TagSummary` を更新し、`GET /api/tags` と static export が `TagSummary` read model を利用できる状態にする。

## タスク種別

機能追加

## スコープ

- repository に `TagSummary` item type、writer、query path を追加する。
- `put_video` / `update_video_tags` 後にタグ件数、latest video、public visibility を再計算する。
- `list_tags` が保存済み `TagSummary` を優先利用し、空の場合は既存の動的 fallback を維持する。
- API / static export / repository tests、README、traceability、DDB audit を更新する。

## 対象外

- 管理 UI での tag category / sort order 編集。
- `VideoTagLink` v0.4 key shape への全面移行。
- 既存 DynamoDB data の TagSummary backfill job。

## 受け入れ条件

- [ ] `TagSummary` item が `pk=TAG#{tag_id}`, `sk=META` で保存される。
- [ ] item に `tag_id`、`label`、`category`、`aliases`、`video_count`、`latest_video_id`、`latest_video_at`、`public_visible`、`sort_order` が含まれる。
- [ ] `put_video` / `update_video_tags` により追加・削除タグの summary が更新される。
- [ ] video_count が 0 になった tag は `public_visible=false` になり、public tag list から除外される。
- [ ] `GET /api/tags` と static export の `/data/tags.json` が TagSummary read model を利用する。
- [ ] README、traceability、DDB schema audit が更新される。
- [ ] targeted tests、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [ ] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. repository に `TagSummary` helper、recompute、list path を追加する。
2. `put_video` の tag index 更新と同じタイミングで summary を再計算する。
3. API / static export / repository tests を更新する。
4. README、traceability、DDB audit、compliance audit を更新する。
5. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_repository_schema_contract.py tests/test_api_handler.py tests/test_static_exporter.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- stale tag が public tag list に残らないこと。
- `TagSummary` がない既存環境でも fallback で tags API/static export が動くこと。
- 管理 UI の未実装を完了扱いしないこと。

## リスク

- 既存 DynamoDB data の backfill は未実装。
- tag category / sort order の管理 UI 編集は後続対象。

## 状態

in_progress
