# FastAPI public detail schema

状態: done

タスク種別: 機能追加

## 背景

`.workspace/plan-20260530.txt` は FastAPI on Lambda を API 正本にし、API-001〜023 の Pydantic request / response schema 証跡を整えることを求めている。API-001/002/003/004/006 は schema baseline 済みだが、動画詳細、成果物一覧、archive calendar、random videos はまだ generic schema のまま。

## 目的

API-005 `GET /api/videos/{video_id}`、API-007 `GET /api/archive-calendar`、API-008 `GET /api/random-videos`、API-009 `GET /api/videos/{video_id}/artifacts` を FastAPI native route + Pydantic response model の対象に追加し、public GET の schema 化を進める。

## スコープ

- detail/archive/random/artifacts の Pydantic response model を追加する。
- 対象 route を FastAPI native route として登録する。
- OpenAPI contract に concrete schema component を追加する。
- `api.zip` 展開後の FastAPI/Mangum entrypoint で対象 route が 200 を返すことを確認する。
- README / traceability / audit と作業完了レポートを更新する。

## スコープ外

- admin route の Pydantic schema 化。
- request query/body parameter の Pydantic model 化。
- 既存 handler route 実装の全面 FastAPI router 化。
- 実 Lambda / CloudFront deploy rehearsal。

## 計画

1. detail/archive/random/artifacts の response shape を確認する。
2. FastAPI native route と Pydantic response model を追加する。
3. OpenAPI contract と tests を更新する。
4. docs と report を更新し、targeted checks と `npm run verify` を実行する。
5. PR 本文・コメント、task done、push まで完了する。

## ドキュメント保守計画

- README の FastAPI schema baseline 記述を API-005/007/008/009 まで拡張する。
- `docs/design/traceability-matrix.md` と `reports/audit/design-v0.4-compliance-20260530.md` を、public GET schema 済み / admin schema は後続として更新する。

## 受け入れ条件

- [x] FastAPI app に detail/archive/random/artifacts の Pydantic response model がある。
- [x] API-005 / API-007 / API-008 / API-009 が FastAPI native route として登録される。
- [x] OpenAPI contract の API-005 / API-007 / API-008 / API-009 が concrete schema component を参照する。
- [x] `api.zip` 展開後の FastAPI/Mangum entrypoint で対象 route が 200 を返す。
- [x] 既存 Lambda handler の route behavior と tests が維持される。
- [x] docs / audit が public GET schema 済みと残る schema gap を区別している。
- [x] 作業完了レポートを `reports/working/` に作成している。

## 検証

- `python3 -m py_compile apps/api/src/diopside_api/fastapi_app.py apps/api/src/diopside_api/openapi_contract.py`
  - passed
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py tests/test_openapi_contract.py tests/test_package_deploy.py`
  - 35 passed
- `npm run package:deploy`
  - passed
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` `/api/videos/fixture001`、`/api/videos/fixture001/artifacts`、`/api/archive-calendar`、`/api/random-videos`
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
- `api.zip` 展開後の `diopside_api.fastapi_lambda.lambda_handler` `/api/videos/fixture001`、`/api/videos/fixture001/artifacts`、`/api/archive-calendar`、`/api/random-videos`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## PR レビュー観点

- public GET response schema が FastAPI/Pydantic の実体を持つこと。
- 既存の fixture fallback、path parameter、query 挙動を壊していないこと。
- admin API schema 完全化を実施済み扱いしていないこと。

## リスク

- response_model validation と既存 response shape にずれがある場合、runtime error になる。
- 今回は public GET schema の baseline であり、admin schema 化には追加作業が必要。

## Done 条件

- 実装、テスト、docs 更新、作業レポート作成、PR 本文更新を完了した。
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4583087983
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4583088563
