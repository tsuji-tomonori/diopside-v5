# FastAPI public list schema

状態: in_progress

タスク種別: 機能追加

## 背景

`.workspace/plan-20260530.txt` は FastAPI on Lambda を API 正本にし、API-001〜023 の Pydantic request / response schema 証跡を整えることを求めている。前段で API-001 `GET /api/health` と API-002 `GET /api/config` は FastAPI native route + Pydantic response model にしたが、public read の主要 list route はまだ generic schema のまま。

## 目的

API-003 `GET /api/home`、API-004 `GET /api/videos`、API-006 `GET /api/tags` を FastAPI native route + Pydantic response model の対象に追加し、public read schema 化を進める。

## スコープ

- home/videos/tags の Pydantic response model を追加する。
- home/videos/tags を FastAPI native route として登録する。
- OpenAPI contract に Home / VideoList / TagList の concrete schema component を追加する。
- `api.zip` 展開後の FastAPI/Mangum entrypoint で home/videos/tags が 200 を返すことを確認する。
- README / traceability / audit と作業完了レポートを更新する。

## スコープ外

- API-005 以降の詳細・admin route の Pydantic schema 化。
- request query/body parameter の Pydantic model 化。
- 既存 handler route 実装の全面 FastAPI router 化。
- 実 Lambda / CloudFront deploy rehearsal。

## 計画

1. home/videos/tags の response shape を確認する。
2. FastAPI native route と Pydantic response model を追加する。
3. OpenAPI contract と tests を更新する。
4. docs と report を更新し、targeted checks と `npm run verify` を実行する。
5. PR 本文・コメント、task done、push まで完了する。

## ドキュメント保守計画

- README の FastAPI schema baseline 記述を API-003/004/006 まで拡張する。
- `docs/design/traceability-matrix.md` と `reports/audit/design-v0.4-compliance-20260530.md` を、public list schema 済み / 残 API schema は後続として更新する。

## 受け入れ条件

- [x] FastAPI app に home/videos/tags の Pydantic response model がある。
- [x] `GET /api/home`、`GET /api/videos`、`GET /api/tags` が FastAPI native route として登録される。
- [x] OpenAPI contract の API-003 / API-004 / API-006 が concrete schema component を参照する。
- [x] `api.zip` 展開後の FastAPI/Mangum entrypoint で home/videos/tags が 200 を返す。
- [x] 既存 Lambda handler の route behavior と tests が維持される。
- [x] docs / audit が public list schema 済みと残る schema gap を区別している。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `python3 -m py_compile apps/api/src/diopside_api/fastapi_app.py apps/api/src/diopside_api/openapi_contract.py`
  - passed
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py tests/test_openapi_contract.py tests/test_package_deploy.py`
  - 35 passed
- `npm run package:deploy`
  - passed
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` `/api/home`、`/api/videos`、`/api/tags`
  - 200 returned
- `api.zip` 展開後の `/api/videos?limit=1`
  - 200 returned、1 item
- `node tools/check-docs-consistency.mjs`
  - passed
- `git diff --check`
  - passed
- `npm run verify`
  - 144 passed、build、package、local e2e passed

## 検証計画

- `python3 -m py_compile apps/api/src/diopside_api/fastapi_app.py apps/api/src/diopside_api/openapi_contract.py`
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py tests/test_openapi_contract.py tests/test_package_deploy.py`
- `npm run package:deploy`
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` `/api/home`、`/api/videos`、`/api/tags`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- public list response schema が FastAPI/Pydantic の実体を持つこと。
- 既存の検索・tag filter・fixture fallback 挙動を壊していないこと。
- 全 API schema 完全化を実施済み扱いしていないこと。

## リスク

- response_model validation と既存 response shape にずれがある場合、runtime error になる。
- 今回は public list schema の baseline であり、detail/admin schema 化には追加作業が必要。
