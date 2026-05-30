# StaticExport history admin view

状態: do

## 背景

v0.4 の `StaticExport` item は public data export の manifest URI、件数、schema versions、content hash、publish state を履歴として保持する。writer/query path は実装済みだが、管理 API/UI 表示が未対応として audit に残っている。

## 目的

管理者が StaticExport 履歴を API と管理 UI から確認できるようにする。

## タスク種別

機能追加

## スコープ

- `GET /api/admin/static-exports` を追加し、`StaticExport` history items を返す。
- 管理 UI に static export 履歴読み込み操作と一覧表示を追加する。
- local fixture mode の API server で fixture manifest 由来の StaticExport item を seed し、local e2e で表示を確認する。
- README、traceability、DDB audit、作業レポートを更新する。

## 計画

1. 既存 `list_static_exports` と API 管理 route を確認する。
2. 管理 API route と response shaping を追加する。
3. 管理 UI と local e2e を更新する。
4. local fixture seed に StaticExport item を追加する。
5. 対象検証と `npm run verify` を実行する。

## ドキュメント保守方針

README の API/UI 説明、`docs/design/traceability-matrix.md`、`docs/design/dynamodb-schema-audit.md`、audit report の StaticExport 差分を更新する。設計書正本は変更しない。

## 受け入れ条件

- `GET /api/admin/static-exports` が cookie session または Bearer fallback で StaticExport 履歴を返す。
- response は `schema_version=admin-static-export-list/v1` と `items` を持つ。
- items は export version、exported_at、manifest URI、public prefix、video/tag count、publish state、content hash、schema versions を含む。
- 管理 UI から static export 履歴を読み込み、主要 field を表示できる。
- local e2e が fixture StaticExport 履歴表示を検証する。
- local fixture seed は local server かつ `DIOPSIDE_LOCAL_FIXTURE_MODE=true` に限定する。
- README、traceability、DDB audit、audit report が更新済みである。
- 選定した検証コマンドが pass し、未実施検証があれば理由を記録する。

## 検証計画

- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py::test_admin_static_export_history_returns_visible_fields`
- `node --check apps/web/public/app.js`
- `python3 -m py_compile apps/api/src/diopside_api/handler.py apps/api/src/diopside_api/local_server.py`
- `node tools/check-web-dom-safety.mjs`
- `node tools/check-docs-consistency.mjs`
- `npm run e2e:local`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- StaticExport history API が管理認証配下であること。
- 本番 UI に固定 export 履歴を表示せず、API items または empty/error state だけを表示すること。
- local fixture seed が本番 handler に入らないこと。
- 返却 field に不要な secret が含まれないこと。
