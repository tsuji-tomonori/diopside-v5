# FastAPI public schema baseline 作業完了レポート

## 受けた指示

`.workspace/plan-20260530.txt` と `.workspace/` の v0.4 設計書を正本として、main を pull 済みの作業ブランチで v0.4 準拠を継続する。今回は FastAPI on Lambda の Pydantic schema / router 移植 gap に対して、public read route の baseline を進めた。

## 要件整理

- `GET /api/health` と `GET /api/config` を FastAPI native route + Pydantic response model にする。
- 既存 `lambda_handler` の route behavior と JSON request log は維持する。
- OpenAPI contract の API-001 / API-002 が具体 schema component を参照する。
- 全 API の schema 完全化は未対応として明記する。

## 検討・判断

- health/config は副作用がなく、既存 handler の認可境界にも触れないため、最初の native route 化対象にした。
- native route は内部で既存 `lambda_handler` を呼び、返却 body を Pydantic model で validate して返す。これにより CloudWatch JSON log と既存 response shape を維持する。
- `from __future__ import annotations` と local import 型の組み合わせでは FastAPI が `request` を query parameter と解釈するため、endpoint signature を明示設定した。

## 実施作業

- `fastapi_app.py` に `HealthResponse` / `PublicConfigResponse` と health/config native route を追加した。
- `openapi_contract.py` に `HealthResponse` / `PublicConfigResponse` / `HealthDependency` schema component を追加し、API-001 / API-002 の response schema を具体化した。
- `tests/test_openapi_contract.py` で concrete schema refs と schema details を検証した。
- README、traceability、v0.4 compliance audit を baseline 済み / 残 schema gap に更新した。

## 成果物

- `apps/api/src/diopside_api/fastapi_app.py`
- `apps/api/src/diopside_api/openapi_contract.py`
- `tests/test_openapi_contract.py`
- README / traceability / audit 更新
- `tasks/do/20260530-2258-fastapi-public-schema-baseline.md`

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

## 指示への fit 評価

- v0.4 の FastAPI on Lambda / API schema 証跡へ向け、health/config を Pydantic response model 付き native route にした。
- 既存 handler 委譲とログは維持しており、認可境界は弱めていない。
- 全 API の Pydantic schema 完全化と router 移植はまだ残る。

## 未対応・制約・リスク

- API-003〜023 と extra admin routes の Pydantic schema 化は未対応。
- 実 Lambda / CloudFront deploy rehearsal は未実施。
- package 時に PyPI dependency を取得するため、offline package には wheel cache や vendor mirror が別途必要。
