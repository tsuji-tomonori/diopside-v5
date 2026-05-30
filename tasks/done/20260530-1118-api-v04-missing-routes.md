# api v0.4 missing routes

状態: done

## 背景

`.workspace/plan-20260530.txt` は v0.4 準拠の P0/P1 として API-001〜023 の照合と未対応 API の実装を求めている。現在の traceability では API-007 `/api/archive-calendar`、API-022 `PUT /api/admin/channels/{channel_id}`、API-023 `POST /api/admin/artifacts/presigned-url` が未対応である。

## 目的

既存の軽量 Lambda handler 構成を維持しつつ、v0.4 の未対応 API-007/API-022/API-023 を実装し、テストと docs/traceability を更新する。

## タスク種別

機能追加

## スコープ

- `GET /api/archive-calendar` を追加する。
- `PUT /api/admin/channels/{channel_id}` を追加する。
- `POST /api/admin/artifacts/presigned-url` を追加する。
- repository に channel 更新と artifact lookup の最小 API を追加する。
- API tests、README、traceability、audit report を更新する。

## 非スコープ

- FastAPI 移行は行わない。
- HttpOnly cookie session 化は行わず、既存 Bearer token + CSRF 境界を維持する。
- 本番 AWS S3 の presigned URL 実発行は boto3 経由で実装するが、local tests では fake S3 client を注入して検証する。
- UI 追加は行わない。

## 計画

1. API 仕様と既存 handler/repository を確認する。
2. repository に `put_channel`、`get_artifact_by_id` 相当を追加する。
3. API handler に archive calendar、channel update、presigned URL route を追加する。
4. 認証・CSRF・入力 validation・許可対象 artifact scope をテストする。
5. README、traceability、audit report を更新する。
6. `git diff --check`、`npm test`、`npm run verify` を実行する。
7. 作業レポート、commit、push、PR 更新コメント、task done 更新を行う。

## ドキュメント保守計画

README の実装済み API 表に API-007/API-022/API-023 を追加する。`docs/design/traceability-matrix.md` の status を更新し、audit report に API P0/P1 の進捗を追記する。

## セキュリティ確認方針

- `GET /api/archive-calendar` は public endpoint とし、公開動画 metadata 由来の年/月/日別集計のみ返す。
- `PUT /api/admin/channels/{channel_id}` は管理認証と CSRF を必須にする。
- `POST /api/admin/artifacts/presigned-url` は管理認証と CSRF を必須にし、対象 artifact は private S3 URI または raw/processed bucket artifact に限定する。public path や任意 URL は署名対象にしない。

## 受け入れ条件

- [x] `GET /api/archive-calendar` が 200 を返し、year/month query の validation と年/月/日別集計がテストされている。
- [x] `PUT /api/admin/channels/{channel_id}` が管理認証 + CSRF を要求し、channel config を保存して返す。
- [x] `POST /api/admin/artifacts/presigned-url` が管理認証 + CSRF を要求し、許可された private artifact だけに短時間 presigned URL を返す。
- [x] unauthorized / CSRF invalid / validation error / not found または forbidden のテストがある。
- [x] README、traceability、audit report が更新されている。
- [x] `git diff --check`、`npm test`、`npm run verify` が pass する。

## 完了メモ

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/40
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581346608
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581347797
- 検証: `py_compile` pass、`tests/test_api_handler.py` pass、`node tools/check-docs-consistency.mjs` pass、`git diff --check` pass、`npm test` pass、`npm run verify` pass
- 残差分: FastAPI/OpenAPI 化、HttpOnly cookie session 化、dev deploy rehearsal は未対応

## 検証計画

- `git diff --check`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_api_handler.py`
- `npm test`
- `npm run verify`

## PR レビュー観点

- 管理系 route に認証・CSRF 抜けがないこと。
- presigned URL が arbitrary S3 key / public URL / non-S3 URI を署名しないこと。
- public archive calendar が公開動画由来の非機微情報だけを返すこと。
- fixed demo data fallback を production path に入れていないこと。

## リスク

- FastAPI/OpenAPI 化は未対応のまま残る。
- 管理 UI の正式 cookie session 化は未対応のまま残る。
