# Admin video tag correction UI 作業完了レポート

## 受けた指示

`.workspace/plan-20260530.txt` と v0.4 基本設計に沿って、main の実装を設計へ寄せる。今回は FR-A-005 の残差分として、管理 UI から動画タグ補正を操作できるようにする。

## 要件整理

- 管理 UI から `video_id` とタグの追加・削除・置換を入力できる。
- add/remove mode は `add_tags` / `remove_tags` を送る。
- replace mode は `replace_tags` だけを送る。
- 送信は既存の cookie session + CSRF flow を使う。
- local e2e が fixture video の tag update と結果表示を確認する。
- 本番 UI に固定 video/tag fallback を入れない。

## 検討・判断

- API/repository は既存実装を使い、UI と e2e coverage を追加した。
- local e2e の公開 fixture は静的 JSON 由来で repository には存在しないため、`DIOPSIDE_LOCAL_FIXTURE_MODE=true` の local server 起動時だけ public fixture video を MemoryRepository に seed する。
- local fixture seed は本番 handler ではなく local server に閉じ、DynamoDB / production path には影響させない。

## 実施作業

- `apps/web/public/index.html` に tag correction form を追加。
- `apps/web/public/app.js` に tag input parser、add/remove/replace body 組み立て、CSRF 付き tag update、結果表示を追加。
- `apps/api/src/diopside_api/local_server.py` に local fixture repository seed を追加。
- `tools/run-local-e2e.mjs` に fixture video の tag update browser flow を追加。
- `README.md`、`docs/design/traceability-matrix.md`、`reports/audit/design-v0.4-compliance-20260530.md` を更新。

## 成果物

- 管理 UI video tag correction flow
- local fixture mode repository seed
- local e2e の tag correction coverage
- FR-A-005 traceability 更新

## 指示への fit 評価

- v0.4 正本は変更せず、実装を FR-A-005 に寄せた。
- Bearer token の localStorage 保存は追加していない。
- 固定 video/tag 表示や demo fallback は本番 UI に追加していない。

## 未対応・制約・リスク

- tag category / sort order の管理 UI 編集は未対応。
- tag 補正後の自動 static export enqueue は未対応。
- 実 AWS 環境での tag update は未確認。

## 検証結果

- `node --check apps/web/public/app.js`: pass
- `python3 -m py_compile apps/api/src/diopside_api/local_server.py`: pass
- `node --check tools/run-local-e2e.mjs`: pass
- `node tools/check-web-dom-safety.mjs`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py::test_admin_video_tag_update_requires_csrf_and_persists tests/test_api_handler.py::test_admin_video_tag_update_validates_body_and_not_found`: pass（2 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `npm run e2e:local`: pass
- `git diff --check`: pass
- `npm run verify`: pass（134 tests + build/package/local e2e）
