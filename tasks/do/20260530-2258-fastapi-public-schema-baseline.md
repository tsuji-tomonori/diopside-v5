# FastAPI public schema baseline

状態: in_progress

タスク種別: 機能追加

## 背景

`.workspace/plan-20260530.txt` は FastAPI on Lambda を API 正本にし、API-001〜023 の schema 証跡を整えることを求めている。前段で FastAPI + Mangum runtime entrypoint は追加済みだが、FastAPI app は全 route を既存 `lambda_handler` へ委譲しており、Pydantic request / response schema の証跡はまだ弱い。

## 目的

安全に切れる public read route のうち `GET /api/health` と `GET /api/config` を FastAPI native route + Pydantic response model の baseline にし、既存 Lambda route behavior と JSON request log を維持しながら schema 化を進める。

## スコープ

- FastAPI app に health/config の Pydantic response model を追加する。
- health/config は FastAPI native route として登録し、既存 `lambda_handler` の結果を model で返す。
- OpenAPI contract に health/config の具体 schema component を追加する。
- package zip 展開後の FastAPI/Mangum entrypoint で health/config が 200 を返すことを確認する。
- README / traceability / audit と作業完了レポートを更新する。

## スコープ外

- API-001〜023 全 route の Pydantic schema 完全化。
- admin POST/PUT request body の Pydantic schema 化。
- route 実装の FastAPI router への全面移植。
- 実 Lambda / CloudFront deploy rehearsal。

## 計画

1. FastAPI adapter と OpenAPI contract の現 shape を確認する。
2. health/config response model と native route を追加する。
3. OpenAPI contract と tests を更新する。
4. docs と report を更新し、targeted checks と `npm run verify` を実行する。
5. PR 本文・コメント、task done、push まで完了する。

## ドキュメント保守計画

- README の FastAPI 説明に health/config schema baseline を追記する。
- `docs/design/traceability-matrix.md` と `reports/audit/design-v0.4-compliance-20260530.md` を、public schema baseline 済み / 全 route schema は後続として更新する。

## 受け入れ条件

- [x] FastAPI app に `HealthResponse` と `PublicConfigResponse` 相当の Pydantic response model がある。
- [x] `GET /api/health` と `GET /api/config` が FastAPI native route として登録される。
- [x] OpenAPI contract の API-001 / API-002 が具体 schema component を参照する。
- [x] `api.zip` 展開後の FastAPI/Mangum entrypoint で health/config が 200 を返す。
- [x] 既存 Lambda handler の route behavior と tests が維持される。
- [x] docs / audit が baseline 済みと残る schema gap を区別している。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `python3 -m py_compile apps/api/src/diopside_api/fastapi_app.py apps/api/src/diopside_api/openapi_contract.py`
  - passed
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py tests/test_openapi_contract.py tests/test_package_deploy.py`
  - 35 passed
- `npm run package:deploy`
  - passed
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` `/api/health` と `/api/config`
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
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` `/api/health` と `/api/config`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- schema baseline が FastAPI/Pydantic の実体を持つこと。
- JSON request log や既存 handler behavior を弱めていないこと。
- 全 route schema 完全化を実施済み扱いしていないこと。

## リスク

- FastAPI response_model を直接使うため、既存 response shape と model 定義にずれがあると runtime validation error になる。
- 今回は health/config の baseline であり、全 API の schema 化には追加作業が必要。
