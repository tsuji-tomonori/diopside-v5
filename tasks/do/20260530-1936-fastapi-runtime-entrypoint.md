# FastAPI runtime entrypoint

状態: in_progress

タスク種別: 機能追加

## 背景

`.workspace/plan-20260530.txt` は P0-04 / P0-06 として FastAPI on Lambda を API 正本にすることを求めている。現状は `apps/api/src/diopside_api/fastapi_app.py` と OpenAPI contract はあるが、deploy package は FastAPI / Mangum 依存を同梱せず、CloudFormation の API Lambda handler は `diopside_api.handler.lambda_handler` のままである。

## 目的

API Lambda の deploy 経路を FastAPI + Mangum entrypoint に寄せ、`api.zip` に runtime dependency を同梱する。既存 route 実装は FastAPI adapter から現 `lambda_handler` に委譲し、API-001〜023 の route behavior を維持する。

## スコープ

- FastAPI + Mangum Lambda entrypoint を追加する。
- `api.zip` に FastAPI / Mangum runtime dependency を同梱する packaging を追加する。
- CloudFormation / CDK synth 対象の API Lambda handler を FastAPI entrypoint に切り替える。
- package deploy / infra contract / FastAPI adapter tests を追加・更新する。
- README / traceability / audit と作業完了レポートを更新する。

## スコープ外

- Pydantic request / response schema の全面定義。
- 既存 handler route 実装の FastAPI router への完全移植。
- 実 Lambda / CloudFront deploy rehearsal。

## 計画

1. 既存 FastAPI adapter、package deploy、CloudFormation handler contract を確認する。
2. Mangum entrypoint と API runtime dependency packaging を追加する。
3. package zip と infra handler の contract tests を追加・更新する。
4. docs と report を更新し、targeted checks と `npm run verify` を実行する。
5. PR 本文・コメント、task done、push まで完了する。

## ドキュメント保守計画

- README の FastAPI/OpenAPI 説明と deploy package 説明を更新する。
- `docs/design/traceability-matrix.md` と `reports/audit/design-v0.4-compliance-20260530.md` を、runtime entrypoint 対応済み / Pydantic schema 完全化は後続として更新する。

## 受け入れ条件

- [x] API Lambda handler が FastAPI + Mangum entrypoint を参照する。
- [x] `api.zip` に `diopside_api/fastapi_lambda.py` と FastAPI / Mangum runtime dependency が含まれる。
- [x] FastAPI adapter が `/api/health` などの既存 route behavior を維持する。
- [x] OpenAPI contract 生成が維持される。
- [x] package deploy、infra contract、API/FastAPI targeted tests が通る。
- [x] docs / audit が「FastAPI runtime entrypoint 済み」と残る schema gap を区別している。
- [x] 作業完了レポートを `reports/working/` に作成している。

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
  - passed
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` `/api/health`
  - 200 returned
- `npm run verify`
  - 144 passed、build、package、local e2e passed

## 検証計画

- `python3 -m py_compile apps/api/src/diopside_api/fastapi_app.py apps/api/src/diopside_api/fastapi_lambda.py tools/package_deploy.py`
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py tests/test_openapi_contract.py tests/test_package_deploy.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py tests/test_cdk_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- Lambda handler が FastAPI/Mangum entrypoint へ切り替わっていること。
- API behavior は既存 handler 委譲で維持し、未実装の Pydantic schema 完全化を実施済み扱いしていないこと。
- package deploy が API dependency を zip 内へ同梱し、worker zip には不要な API dependency を混ぜていないこと。

## リスク

- FastAPI / Mangum dependency install に network access が必要になる可能性がある。
- 今回は FastAPI runtime 化であり、各 route の Pydantic schema 完全化は後続。
