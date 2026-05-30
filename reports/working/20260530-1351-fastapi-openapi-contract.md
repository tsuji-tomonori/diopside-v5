# FastAPI / OpenAPI contract 作業レポート

## 指示

- `.workspace/plan-20260530.txt` の v0.4 設計準拠対応を継続する。
- main を pull してから、Worktree Task PR Flow に従い task md、実装、検証、レポート、PR 反映まで進める。

## 要件整理

- v0.4 の P0-04/P0-06 に対し、FastAPI on Lambda と API-001〜023 の OpenAPI 証跡を追加する。
- 既存 Lambda handler の挙動と deploy entrypoint は壊さない。
- ローカル環境には `fastapi` / `mangum` がないため、依存なしで OpenAPI contract を生成・検証できる必要がある。
- FastAPI/Mangum 依存同梱、Lambda entrypoint 切替、Pydantic schema 完全化は対象外。

## 実施作業

- root `main` で `git pull --ff-only` を実行し、`Already up to date` を確認した。
- `apps/api/src/diopside_api/openapi_contract.py` を追加し、API-001〜023 と追加管理 route の OpenAPI 3.1 contract を生成できるようにした。
- `apps/api/src/diopside_api/fastapi_app.py` を追加し、FastAPI がインストールされた環境で既存 `lambda_handler` へ委譲する app factory を用意した。
- `tests/test_openapi_contract.py` を追加し、API-001〜023 の design id、path/method、主要 schema version、README/handler との整合を検証した。
- README、traceability matrix、compliance audit を更新し、FastAPI adapter / OpenAPI contract は部分実装であり runtime 切替は未対応であることを明記した。

## 成果物

- `apps/api/src/diopside_api/openapi_contract.py`
- `apps/api/src/diopside_api/fastapi_app.py`
- `tests/test_openapi_contract.py`
- `README.md`
- `docs/design/traceability-matrix.md`
- `reports/audit/design-v0.4-compliance-20260530.md`
- `tasks/do/20260530-1347-fastapi-openapi-contract.md`

## 検証

- `python3 -m py_compile apps/api/src/diopside_api/openapi_contract.py apps/api/src/diopside_api/fastapi_app.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_openapi_contract.py tests/test_api_handler.py`: pass、30 tests
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m diopside_api.openapi_contract`: pass、OpenAPI JSON を出力
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass、114 tests + build + package + local e2e
- `unzip -l build/deploy/api.zip | rg "diopside_api/(fastapi_app|openapi_contract)\\.py"`: pass

## Fit 評価

- 総合fit: 4.2 / 5.0
- API-001〜023 の OpenAPI 3.1 contract と FastAPI adapter は追加できた。
- FastAPI/Mangum 依存同梱と Lambda runtime entrypoint の切替は未対応のため、v0.4 の FastAPI on Lambda 完全準拠ではなく段階的な部分準拠である。

## 未対応・制約・リスク

- `fastapi` / `mangum` はローカル環境に未インストールで、実 FastAPI app 起動は未検証。
- OpenAPI schema は path/method/schema_version 中心で、Pydantic request/response model の完全表現ではない。
- deploy runtime は引き続き既存 `diopside_api.handler.lambda_handler` を entrypoint とする。
