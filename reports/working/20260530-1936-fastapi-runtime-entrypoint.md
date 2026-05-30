# FastAPI runtime entrypoint 作業完了レポート

## 受けた指示

`.workspace/plan-20260530.txt` と `.workspace/` の v0.4 設計書を正本として、main を pull 済みの作業ブランチで v0.4 準拠を継続する。今回は P0-04 / P0-06 の FastAPI on Lambda 差分を進めた。

## 要件整理

- API Lambda の runtime entrypoint を FastAPI + Mangum に寄せる。
- `api.zip` に FastAPI / Mangum runtime dependency を同梱する。
- 既存 API behavior は FastAPI adapter から現 `lambda_handler` へ委譲して維持する。
- Pydantic schema 全面定義や FastAPI router への完全移植は未実施として明記する。

## 検討・判断

- 現 route 実装は `handler.py` にまとまっているため、今回の scope では `fastapi_app.py` から既存 `lambda_handler` へ委譲する構造を維持した。
- `diopside_api.fastapi_lambda.lambda_handler` を Mangum entrypoint とし、CloudFormation の `ApiFunction.Handler` を切り替えた。
- API dependency は `requirements-api.txt` に分け、`tools/package_deploy.py` が API zip のみに install target を追加する。worker zip には FastAPI / Mangum を混ぜない。
- FastAPI endpoint factory は `Request` annotation を明示しないと query parameter と扱われるため、runtime signature を設定して Lambda event からの `/api/health` が 200 になることを確認した。

## 実施作業

- `apps/api/src/diopside_api/fastapi_lambda.py` を追加した。
- `requirements-api.txt` に `fastapi==0.115.12` と `mangum==0.19.0` を追加した。
- `tools/package_deploy.py` を API runtime dependency 同梱に対応させた。
- `infra/cloudformation/diopside.yaml` の API Lambda handler を `diopside_api.fastapi_lambda.lambda_handler` へ変更した。
- `tests/test_package_deploy.py` と `tests/test_cloudformation_contract.py` を更新し、API zip dependency と handler contract を固定した。
- README、traceability、v0.4 compliance audit を更新した。
- BATCH-006 の既存 test が実行時刻に依存していたため、`now` を明示して deterministic にした。

## 成果物

- `apps/api/src/diopside_api/fastapi_lambda.py`
- `requirements-api.txt`
- `tools/package_deploy.py`
- `infra/cloudformation/diopside.yaml`
- `tests/test_package_deploy.py`
- `tests/test_cloudformation_contract.py`
- `tests/test_core_pipeline.py`
- README / traceability / audit 更新
- `tasks/do/20260530-1936-fastapi-runtime-entrypoint.md`

## 検証

- `python3 -m py_compile apps/api/src/diopside_api/fastapi_app.py apps/api/src/diopside_api/fastapi_lambda.py tools/package_deploy.py`
  - passed
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py tests/test_openapi_contract.py tests/test_package_deploy.py`
  - 35 passed
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py tests/test_cdk_contract.py`
  - 20 passed
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_notification_plan_creates_due_items_idempotently tests/test_core_pipeline.py::test_notification_plan_delivers_due_items_and_records_states`
  - 2 passed
- `node tools/check-docs-consistency.mjs`
  - passed
- `git diff --check`
  - passed
- `npm run package:deploy`
  - passed。初回は sandbox network 制限で失敗し、承認後に PyPI 依存取得を実行した。
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` `/api/health`
  - 200 returned
- `npm run verify`
  - 144 passed、build、package、local e2e passed

## 指示への fit 評価

- v0.4 の FastAPI on Lambda へ向け、deploy package と Lambda handler を FastAPI + Mangum runtime entrypoint に寄せた。
- API-001〜023 の route behavior は既存 handler 委譲で維持した。
- Pydantic schema 完全化と FastAPI router への完全移植は後続課題として明記した。

## 未対応・制約・リスク

- 実 Lambda / CloudFront deploy rehearsal は未実施。
- Pydantic request / response schema の全面定義は未対応。
- package 時に PyPI から dependency を取得するため、offline package には wheel cache や vendor mirror が別途必要。
