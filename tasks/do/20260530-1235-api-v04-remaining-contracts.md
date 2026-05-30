# API v0.4 remaining contracts

## 背景

`.workspace/plan-20260530.txt` は API-001〜023 の完全実装と正常系/認証エラー/validation エラーのテストを完了条件にしている。
現状の traceability では API-008、API-009、API-013、API-015、API-016、API-019 が route 実装済み候補である一方、テスト証跡不足のため `部分実装` として残っている。

## 目的

既存 route の contract test を追加し、API-008/009/013/015/016/019 を v0.4 の API coverage 上 `実装済` に近づける。

## タスク種別

機能追加

## スコープ

- `GET /api/random-videos` の schema / limit contract をテストする。
- `GET /api/videos/{video_id}/artifacts` の fixture/repository contract と 404 をテストする。
- `POST /api/admin/jobs/live-status-scan` / `chat-normalize` / `rebuild-artifacts` / `{job_id}/cancel` の正常系と validation/auth/CSRF 境界をテストする。
- traceability と作業レポートを更新する。

## 対象外

- FastAPI / OpenAPI 移行。
- route 実装の大規模変更。
- 実 SQS 送信、実 DynamoDB、実 AWS での smoke。

## 受け入れ条件

- [ ] API-008 `GET /api/random-videos` の正常系 contract test がある。
- [ ] API-009 `GET /api/videos/{video_id}/artifacts` の正常系と not found test がある。
- [ ] API-013/API-015/API-016/API-019 の管理 job API が認証/CSRF/validation を含めてテストされる。
- [ ] `docs/design/traceability-matrix.md` で対象 API の tests/status が更新される。
- [ ] targeted API test、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [ ] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. `tests/test_api_handler.py` に public API-008/009 の contract tests を追加する。
2. 管理 job API の dry-run tests を既存 helper で追加する。
3. validation / CSRF 境界を既存 admin auth test と重複しすぎない形で確認する。
4. traceability の tests/status を更新する。
5. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## ドキュメント保守計画

API route 自体は README に記載済みのため、主に `docs/design/traceability-matrix.md` の tests/status を更新する。

## 検証計画

- `python3 -m py_compile apps/api/src/diopside_api/handler.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_api_handler.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- route 実装が実際にある API だけを `実装済` として扱うこと。
- 認証/CSRF/validation を未検証のまま完了扱いしないこと。
- 実 AWS SQS 送信を dry-run test で実施済みのように書かないこと。

## リスク

- FastAPI / OpenAPI の完全準拠は未対応のまま残る。
- 実 SQS 送信は未検証で、dry-run path の contract に限定する。

## 状態

in_progress
