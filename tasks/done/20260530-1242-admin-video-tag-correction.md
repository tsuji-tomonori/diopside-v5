# Admin video tag correction

## 背景

`.workspace/plan-20260530.txt` は v0.4 の P1 としてタグ補正を挙げている。
設計 v0.4 の FR-A-005 は「自動タグに対して手動タグを追加・削除でき、静的 JSON へ反映できる」ことを求めているが、現状は動画登録時の `tags` と公開 tag index はある一方、管理 API からタグを補正する経路がない。

## 目的

管理 API で動画タグを追加・削除できるようにし、repository の `Video` item と `VideoTagIndex` を更新して static export に反映できる状態にする。

## タスク種別

機能追加

## スコープ

- `PUT /api/admin/videos/{video_id}/tags` を追加する。
- body の `add_tags` / `remove_tags` / `replace_tags` を validation する。
- repository の tag 更新時に stale `VideoTagIndex` を削除する。
- API / repository / static export tests と traceability / README を更新する。

## 対象外

- 管理 UI のタグ編集画面。
- `VideoTagLink` / `TagSummary` v0.4 key schema への全面移行。
- static export job の自動起動。

## 受け入れ条件

- [x] `PUT /api/admin/videos/{video_id}/tags` が認証 + CSRF 必須で利用できる。
- [x] `add_tags` / `remove_tags` / `replace_tags` によって `Video.tags` が更新される。
- [x] タグ削除時に stale `VideoTagIndex` が残らない。
- [x] static export が更新後のタグを `/data/tags.json` と動画詳細 JSON に反映する。
- [x] FR-A-005 の traceability / audit / README が更新される。
- [x] targeted tests、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [x] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. repository に `update_video_tags` と stale tag index 削除を追加する。
2. API handler に `PUT /api/admin/videos/{video_id}/tags` を追加し、body validation と CSRF 境界を実装する。
3. API / repository / static exporter tests を追加する。
4. README、traceability、audit を更新する。
5. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## ドキュメント保守計画

README の API table に管理タグ補正 API を追加し、`docs/design/traceability-matrix.md` の FR-A-005 を部分実装へ更新する。v0.4 正本は変更しない。

## 検証計画

- `python3 -m py_compile apps/api/src/diopside_api/handler.py apps/shared/src/diopside_core/repository.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_api_handler.py tests/test_repository_schema_contract.py tests/test_static_exporter.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- タグ削除後に stale index が残らず、検索/タグ一覧へ古いタグが出ないこと。
- 未認証または CSRF なしでタグ更新できないこと。
- 管理 UI は未対応であることを完了扱いしないこと。

## リスク

- `VideoTagLink` / `TagSummary` v0.4 schema ではなく、現行 `Video.tags` / `VideoTagIndex` の補正に留まる。
- static export の再実行は別途必要で、自動 enqueue は行わない。

## 完了結果

- 実装 commit: `279279e` (`✨ feat(api): 管理タグ補正APIを追加`)
- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/40
- PR 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581560634
- PR セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581560636
- 作業レポート: `reports/working/20260530-1245-admin-video-tag-correction-report.md`

### 検証結果

- `python3 -m py_compile apps/api/src/diopside_api/handler.py apps/shared/src/diopside_core/repository.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_api_handler.py tests/test_repository_schema_contract.py tests/test_static_exporter.py`: pass（38 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（102 tests + build/package/local e2e）

### 後続対象

- 管理 UI のタグ編集画面。
- `VideoTagLink` / `TagSummary` v0.4 schema への全面移行。
- static export job の自動起動。
- 実 DynamoDB / 実 API / 実 static export job の AWS 経路確認。

## 状態

done
