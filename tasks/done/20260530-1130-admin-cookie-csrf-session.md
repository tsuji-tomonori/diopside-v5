# admin cookie csrf session

- 状態: done
- 種別: 機能追加
- 対象: `ADMIN-SESSION`, `NFR-SEC-005`

## 背景

v0.4 設計では管理 UI/API を HttpOnly cookie + CSRF で保護する前提だが、現状は管理 UI が Bearer token と CSRF token を直接入力して API に送信している。ブラウザ管理 UI を session cookie + CSRF に寄せつつ、CLI や GitHub Actions 向けの既存 Bearer fallback は維持する。

## 受け入れ条件

- `POST /api/admin/session` が管理 passphrase/token を検証し、HttpOnly / Secure / SameSite=Lax の session cookie と `csrf_token` を返す。
- `GET /api/admin/me` が cookie session を検証し、管理 session 情報と `csrf_token` を返す。
- 管理 GET API は Bearer header なしの cookie session で利用できる。
- 管理 POST/PUT API は cookie session と CSRF header を要求し、cookie 不足は 401、CSRF 不足または不一致は 403 を返す。
- CLI / automation 用に既存の Bearer token + CSRF fallback は維持する。
- 管理 UI は Bearer token を保存・送信せず、session cookie と API から返る CSRF token で管理 job を起動する。
- local e2e のブラウザ管理 flow は session login 経由に更新する。
- API unit test と docs consistency check が更新済み contract を検証する。

## 検証予定

- `python3 -m py_compile apps/api/src/diopside_api/handler.py apps/shared/src/diopside_core/repository.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_api_handler.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm test`
- `npm run verify`

## 完了結果

- 実装 commit: `eca00e7`
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581377107
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581377108
- 作業レポート: `reports/working/20260530-1137-admin-cookie-csrf-session-report.md`

## 検証結果

- `python3 -m py_compile apps/api/src/diopside_api/handler.py apps/shared/src/diopside_core/repository.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_api_handler.py`: pass（17 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm test`: pass（78 tests）
- `npm run verify`: pass（test / build / package / local e2e）
