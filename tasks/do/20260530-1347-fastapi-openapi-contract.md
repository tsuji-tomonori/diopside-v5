# FastAPI / OpenAPI contract

## 背景

`.workspace/plan-20260530.txt` は v0.4 の P0 として FastAPI on Lambda と API-001〜023 の schema 証跡を検収基準に戻す方針を示している。
現状の API は `apps/api/src/diopside_api/handler.py` の軽量 Lambda handler 中心で、API route coverage は進んだが FastAPI app と OpenAPI contract は未対応のまま残っている。
ローカル環境には `fastapi` / `mangum` が未インストールであり、依存取得なしに検証できる証跡が必要である。

## 目的

既存 Lambda handler を壊さず、FastAPI adapter と dependency-free な OpenAPI contract を追加し、API-001〜023 の path/method/schema 証跡を repo 内で検証できる状態にする。

## タスク種別

機能追加

## スコープ

- `diopside_api.openapi_contract` を追加し、API-001〜023 と追加管理 route の OpenAPI 3.1 contract を生成する。
- `diopside_api.fastapi_app` を追加し、FastAPI がインストールされた環境で既存 `lambda_handler` へ委譲する app factory を提供する。
- OpenAPI contract test を追加し、API-001〜023 が欠けた場合に検出する。
- README、traceability、compliance audit を更新する。

## 対象外

- Lambda runtime package への `fastapi` / `mangum` 依存同梱。
- 既存 Lambda entrypoint の FastAPI への完全切替。
- Pydantic schema の完全実装。
- API Gateway / Function URL routing の infra 変更。

## 受け入れ条件

- [ ] `apps/api/src/diopside_api/fastapi_app.py` に FastAPI app factory がある。
- [ ] FastAPI 未インストール環境でも通常 tests/package が失敗しない。
- [ ] `apps/api/src/diopside_api/openapi_contract.py` が OpenAPI 3.1 JSON を生成できる。
- [ ] OpenAPI contract に API-001〜023 の method/path が全て含まれる。
- [ ] OpenAPI contract に主要 `schema_version` が記録される。
- [ ] 既存 `lambda_handler` route と OpenAPI contract の route set が test で照合される。
- [ ] README、traceability、compliance audit が更新される。
- [ ] targeted tests、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [ ] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. API route metadata と OpenAPI generator を追加する。
2. FastAPI optional adapter を追加し、既存 handler への委譲で挙動互換を保つ。
3. OpenAPI contract tests を追加する。
4. README、traceability、compliance audit を更新する。
5. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## ドキュメント保守計画

- README の API セクションに OpenAPI contract と FastAPI adapter の位置づけを追記する。
- `docs/design/traceability-matrix.md` の API/FASTAPI 証跡を更新する。
- `reports/audit/design-v0.4-compliance-20260530.md` の P0-04/P0-06 を、完全移行ではなく contract/adapter 追加済みとして更新する。

## 検証計画

- `python3 -m py_compile apps/api/src/diopside_api/openapi_contract.py apps/api/src/diopside_api/fastapi_app.py`
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_openapi_contract.py tests/test_api_handler.py`
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m diopside_api.openapi_contract`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- FastAPI 未インストール環境で既存 CI を壊さないこと。
- OpenAPI contract が実装済み route と乖離しないこと。
- FastAPI 完全移行や dependency 同梱を実施済み扱いしないこと。
- 管理 API の認可境界を adapter で弱めないこと。

## リスク

- FastAPI / Mangum 依存同梱は未対応のため、runtime entrypoint は既存 Lambda handler のままである。
- OpenAPI schema は path/method/schema_version の contract に留まり、Pydantic model の完全な request/response schema ではない。

## 状態

in_progress
