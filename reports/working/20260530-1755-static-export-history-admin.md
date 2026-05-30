# StaticExport history admin view 作業完了レポート

## 受けた指示

`.workspace/plan-20260530.txt` と v0.4 基本設計に沿って、main の実装を設計へ寄せる。今回は `StaticExport` 履歴の残差分として、管理 API/UI から export 履歴を確認できるようにする。

## 要件整理

- 管理認証配下で StaticExport 履歴を返す API を追加する。
- 管理 UI から static export 履歴を読み込み、export version、件数、manifest、state などを表示する。
- local e2e が fixture StaticExport 履歴表示を検証する。
- 本番 UI に固定履歴 fallback を入れない。
- docs/traceability/audit を更新する。

## 検討・判断

- repository の `list_static_exports` は実装済みのため、API/UI 表示に限定した。
- API response は `pk` / `sk` など物理 key を返さず、管理 UI に必要な visible fields へ整形した。
- local fixture mode の e2e では実 static export job を走らせず、local server 起動時に fixture manifest 由来の `StaticExport` item を MemoryRepository に seed する。

## 実施作業

- `GET /api/admin/static-exports` を追加し、`admin-static-export-list/v1` を返すようにした。
- OpenAPI contract と docs consistency の API route/schema 期待値を更新した。
- 管理 UI に static export 履歴読み込み button と一覧表示を追加した。
- local fixture seed に `StaticExport` item を追加し、local e2e で表示確認した。
- README、DDB schema audit、traceability、audit report を更新した。

## 成果物

- `GET /api/admin/static-exports`
- 管理 UI static export history list
- local e2e の StaticExport history coverage
- StaticExport audit 更新

## 指示への fit 評価

- v0.4 正本は変更せず、実装を `StaticExport` history の API/UI 表示に寄せた。
- 管理 API は既存 admin auth 配下に置いた。
- 固定 export 履歴表示や demo fallback は本番 UI に追加していない。

## 未対応・制約・リスク

- 既存 StaticExport item の backfill は未対応。
- 過去 export の `superseded` 更新は未対応。
- 実 AWS 環境での履歴表示は未確認。

## 検証結果

- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py::test_admin_static_export_history_returns_visible_fields`: pass
- `node --check apps/web/public/app.js`: pass
- `python3 -m py_compile apps/api/src/diopside_api/handler.py apps/api/src/diopside_api/local_server.py apps/api/src/diopside_api/openapi_contract.py`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `node tools/check-web-dom-safety.mjs`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m diopside_api.openapi_contract`: pass
- `npm run e2e:local`: pass
- `git diff --check`: pass
- `npm run verify`: pass（135 tests + build/package/local e2e）
