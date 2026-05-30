# FastAPI public detail schema 作業完了レポート

## 受けた指示

`.workspace/plan-20260530.txt` と `.workspace/` の v0.4 設計書を正本として、main を pull 済みの作業ブランチで v0.4 準拠を継続する。今回は FastAPI on Lambda の Pydantic schema / router 移植 gap に対して、public GET の detail 系 route を進めた。

## 要件整理

- API-005 / API-007 / API-008 / API-009 を FastAPI native route + Pydantic response model にする。
- 既存 `lambda_handler` の route behavior、fixture fallback、path parameter、query 挙動、JSON request log は維持する。
- OpenAPI contract の対象 API が concrete schema component を参照する。
- admin route の schema 完全化は未対応として明記する。

## 検討・判断

- 対象 route は public GET であり、admin 認可境界に触れないため、public list schema に続く baseline として扱った。
- native route は既存 `lambda_handler` を呼び、返却 body を Pydantic model で validate して返す。既存 handler が持つ path/query 処理と log を維持する。
- detail / artifact / archive の response は既存追加 field を落とさないよう `extra=allow` にした。

## 実施作業

- `fastapi_app.py` に `PublicVideoDetailResponse`、`PublicArchiveCalendarResponse`、`PublicRandomVideosResponse`、`PublicVideoArtifactsResponse` と関連 item models を追加した。
- API-005 / API-007 / API-008 / API-009 を FastAPI native route として登録した。
- `openapi_contract.py` に対象 concrete schema component を追加した。
- `tests/test_openapi_contract.py` で concrete schema refs と nested item refs を検証した。
- README、traceability、v0.4 compliance audit を public GET API-001〜009 schema baseline 済み / 管理 API schema は後続に更新した。

## 成果物

- `apps/api/src/diopside_api/fastapi_app.py`
- `apps/api/src/diopside_api/openapi_contract.py`
- `tests/test_openapi_contract.py`
- README / traceability / audit 更新
- `tasks/do/20260530-2316-fastapi-public-detail-schema.md`

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

## 指示への fit 評価

- v0.4 の FastAPI on Lambda / API schema 証跡へ向け、public GET API-001〜009 を Pydantic response model 付き native route にした。
- 既存 handler 委譲とログは維持しており、認可境界は弱めていない。
- 管理 API の Pydantic schema 完全化と router 移植はまだ残る。

## 未対応・制約・リスク

- API-010〜023 と extra admin routes の Pydantic schema 化は未対応。
- 実 Lambda / CloudFront deploy rehearsal は未実施。
- package 時に PyPI dependency を取得するため、offline package には wheel cache や vendor mirror が別途必要。
