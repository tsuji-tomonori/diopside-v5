# Admin channel settings UI

状態: done

## 背景

v0.4 の FR-A-001 は対象チャンネル設定管理を要求している。API-021/022 と repository writer は実装済みだが、管理 UI は job / quota / job detail 中心で、ブラウザから channel config を一覧・更新できない。

## 目的

管理 UI から `GET /api/admin/channels` と `PUT /api/admin/channels/{channel_id}` を使い、対象チャンネル設定を確認・更新できるようにする。

## タスク種別

機能追加

## スコープ

- `apps/web/public/index.html` の管理 dialog に channel settings controls を追加する。
- `apps/web/public/app.js` で channel list load、既存 channel の form 反映、channel config PUT を実装する。
- `apps/web/public/styles.css` で channel list/form 表示を既存管理 UI に合わせる。
- local e2e 用 API server が `PUT` を handler へ委譲できるようにする。
- local e2e で channel config 更新と一覧反映を確認する。
- README、traceability、作業レポートを更新する。

## 計画

1. 既存管理 UI と API contract を確認する。
2. 管理 dialog に channel controls を追加する。
3. JS に channel list / update flow を追加する。
4. local e2e と docs を更新する。
5. 対象検証と `npm run verify` を実行する。

## ドキュメント保守方針

README の管理 UI 説明、`docs/design/traceability-matrix.md` の FR-A-001 evidence を更新する。設計書正本は変更しない。

## 受け入れ条件

- 管理 UI から channel 一覧を読み込める。
- channel 一覧の item を選択すると channel form に反映される。
- 管理 UI から `channel_id`、`uploads_playlist_id`、`display_name`、`enabled`、`notification_enabled`、interval を更新できる。
- 更新時は cookie session + CSRF token を使い、Bearer token を localStorage に保存しない。
- local e2e が channel update と channel list 反映を検証する。
- README と traceability が更新済みである。
- 選定した検証コマンドが pass し、未実施検証があれば理由を記録する。

## 検証計画

- `node tools/check-web-dom-safety.mjs`
- `npm run e2e:local`
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py::test_admin_channel_update_requires_csrf_and_persists tests/test_api_handler.py::test_admin_channel_update_validates_body`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- 本番 UI に架空 channel を表示せず、API item または empty/error state だけを表示していること。
- channel 更新 POST/PUT が CSRF 付き cookie session を使うこと。
- 管理 UI の既存 job 操作と local e2e を壊していないこと。
- local e2e server が本番 handler と同じ method coverage を持ち、`PUT` route を 501 にしないこと。

## 完了結果

- 管理 UI から channel list を読み込み、API item を選択して form に反映できるようにした。
- 管理 UI から `channel_id`、`uploads_playlist_id`、`display_name`、取得有効/無効、通知候補生成、metadata/live scan interval を更新できるようにした。
- channel update は既存の cookie session + CSRF flow を使い、Bearer token の localStorage 保存は追加していない。
- local e2e server に `PUT` method 委譲を追加し、既存管理 PUT API を browser flow で検証できるようにした。
- README、traceability、audit、作業レポートを更新した。
- 作業レポート: `reports/working/20260530-1724-admin-channel-settings-ui.md`
- PR 受け入れ条件コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582290527
- PR セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4582290524

## 検証結果

- `node --check apps/web/public/app.js`: pass
- `python3 -m py_compile apps/api/src/diopside_api/local_server.py`: pass
- `node tools/check-web-dom-safety.mjs`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py::test_admin_channel_update_requires_csrf_and_persists tests/test_api_handler.py::test_admin_channel_update_validates_body`: pass（2 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `npm run e2e:local`: pass
- `git diff --check`: pass
- `npm run verify`: pass（134 tests + build/package/local e2e）

## 未実施・制約

- 実 AWS 環境での channel update は未実施。理由: dev/prod DynamoDB への実データ変更を伴うため、環境指定後に実施する。
- 既存 DynamoDB data の ChannelRef/AppConfig backfill と AppConfig 統合画面は後続対象。
