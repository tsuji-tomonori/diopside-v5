# Admin video tag correction UI

状態: do

## 背景

v0.4 の FR-A-005 は管理者が自動タグに対して手動タグを追加・削除し、静的 JSON へ反映できることを要求している。API と repository 更新経路は実装済みだが、管理 UI からタグ補正を操作できない。

## 目的

管理 UI から `PUT /api/admin/videos/{video_id}/tags` を使い、動画タグを追加・削除・置換できるようにする。

## タスク種別

機能追加

## スコープ

- `apps/web/public/index.html` の管理 dialog に video tag correction controls を追加する。
- `apps/web/public/app.js` で add/remove/replace tags を CSRF 付きで送信し、結果を表示する。
- local e2e 用 API server が fixture public videos を local repository に seed し、tag update 成功 flow を検証できるようにする。
- local e2e で tag update と結果表示を検証する。
- README、traceability、audit、作業レポートを更新する。

## 計画

1. 既存 tag update API と local fixture repository 状態を確認する。
2. 管理 dialog に tag correction controls を追加する。
3. JS に tag correction submit flow を追加する。
4. local server fixture seed と e2e を更新する。
5. 対象検証と `npm run verify` を実行する。

## ドキュメント保守方針

README の管理 UI 説明、`docs/design/traceability-matrix.md` の FR-A-005 evidence、audit の P1 タグ補正記述を更新する。設計書正本は変更しない。

## 受け入れ条件

- 管理 UI から `video_id` と `add_tags` / `remove_tags` / `replace_tags` を入力できる。
- add/remove mode は `add_tags` と `remove_tags` を string array として送る。
- replace mode は `replace_tags` だけを送り、add/remove と同時送信しない。
- tag update は cookie session + CSRF token を使い、Bearer token を localStorage に保存しない。
- local e2e が fixture video の tag update と結果表示を検証する。
- local fixture mode 以外の本番経路に demo fallback を追加しない。
- README、traceability、audit が更新済みである。
- 選定した検証コマンドが pass し、未実施検証があれば理由を記録する。

## 検証計画

- `node --check apps/web/public/app.js`
- `python3 -m py_compile apps/api/src/diopside_api/local_server.py`
- `node tools/check-web-dom-safety.mjs`
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py::test_admin_video_tag_update_requires_csrf_and_persists tests/test_api_handler.py::test_admin_video_tag_update_validates_body_and_not_found`
- `node tools/check-docs-consistency.mjs`
- `npm run e2e:local`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- 本番 UI に固定 video/tag を表示せず、入力値または API 結果だけを表示していること。
- local fixture seed は `DIOPSIDE_LOCAL_FIXTURE_MODE=true` の local server に限定されていること。
- replace mode が add/remove と同時に送られないこと。
- tag update が既存 session/CSRF flow を使うこと。
