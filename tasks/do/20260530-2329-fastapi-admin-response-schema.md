# FastAPI admin response schema

状態: in_progress

タスク種別: 機能追加

## 背景

`.workspace/plan-20260530.txt` は FastAPI on Lambda を API 正本にし、API-001〜023 の Pydantic request / response schema 証跡を整えることを求めている。public GET API-001〜009 は FastAPI native route + Pydantic response model 済みだが、管理 API は OpenAPI 上で generic response のまま残っている。

## 目的

API-010〜023 と追加管理 route のうち、既存 handler の認証・CSRF 境界を維持したまま、FastAPI native route 登録と concrete Pydantic response model を追加し、管理 API の schema gap を縮小する。

## スコープ

- 管理 API response model を FastAPI app に追加する。
- 管理 API route を FastAPI native route として登録し、既存 `lambda_handler` へ委譲する。
- OpenAPI contract の管理 API response schema を concrete component 参照に更新する。
- 管理 API schema component の contract test を追加する。
- README / traceability / audit と作業完了レポートを更新する。

## スコープ外

- 既存 handler の認証・CSRF ロジックを FastAPI dependency へ全面移植すること。
- 管理 API request body の FastAPI/Pydantic validation を正本にすること。
- 実 AWS / CloudFront deploy rehearsal。

## セキュリティ確認方針

- 管理 API の route は既存 `lambda_handler` に委譲し、`_require_admin` と `_require_csrf` の認証・認可境界を変更しない。
- public route と admin route の OpenAPI `security` 設定を維持する。
- response schema 追加で署名 URL や secret を public route へ露出させない。

## 計画

1. 管理 API の response shape と schema_version を確認する。
2. FastAPI app に管理 API 用 Pydantic response model と native route を追加する。
3. OpenAPI contract と tests を concrete schema component に更新する。
4. docs / audit / report を更新し、targeted checks と `npm run verify` を実行する。
5. PR 本文・コメント、task done、push まで完了する。

## ドキュメント保守計画

- README の FastAPI schema baseline 記述を管理 API response schema まで拡張する。
- `docs/design/traceability-matrix.md` と `reports/audit/design-v0.4-compliance-20260530.md` を、管理 API response schema 済み / request validation と dependency 移植は後続として更新する。

## 受け入れ条件

- [x] FastAPI app に管理 API response model がある。
- [x] API-010〜023 と追加管理 route が FastAPI native route として登録される。
- [x] OpenAPI contract の管理 API response が concrete schema component を参照する。
- [x] 管理 API の認証・CSRF behavior が既存 tests で維持される。
- [x] docs / audit が response schema 済みと残る request/dependency gap を区別している。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `python3 -m py_compile apps/api/src/diopside_api/fastapi_app.py apps/api/src/diopside_api/openapi_contract.py`
  - passed
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py tests/test_openapi_contract.py tests/test_package_deploy.py`
  - 35 passed
- `npm run package:deploy`
  - passed
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` `/api/admin/session`、`/api/admin/me`、`/api/admin/jobs`、`/api/admin/channels`、`/api/admin/quota-usage`
  - 200 returned
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
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` 管理 GET/session route execution
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- 管理 API が OpenAPI/Pydantic の具体 response schema を持つこと。
- 既存 handler の認証・CSRF 境界を弱めていないこと。
- request validation / dependency 移植を実施済み扱いしていないこと。

## リスク

- response_model validation と既存 response shape にずれがある場合、runtime error になる。
- 今回は response schema baseline であり、request schema と FastAPI dependency 化には追加作業が必要。
