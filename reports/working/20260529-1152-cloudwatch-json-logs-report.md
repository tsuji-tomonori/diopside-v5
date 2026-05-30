# CloudWatch JSONログ 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan ファイルに基づき、main から pull してから作業する。
- P2-06 `CloudWatch JSONログ` として、API/worker が `trace_id`、`job_id`、`video_id`、`result`、`duration_ms`、`error` を JSON で出すようにする。

## 要件整理

- API request の成功/失敗を 1 行 JSON log として stdout へ出力する。
- worker job の成功/失敗を 1 行 JSON log として stdout へ出力する。
- 既存の ErrorResponse、JobEvent、failed debug artifact の挙動を壊さない。
- token、CSRF token、YouTube API key、payload 全体は log へ出さない。
- README に CloudWatch Logs での調査観点を追記する。

## 検討・判断

- CloudWatch Lambda logs は stdout を取り込むため、Python 標準の `print(json.dumps(...), flush=True)` で 1 行 JSON を出す最小構成にした。
- API は既存の `trace_id` response header/body を維持し、request 完了時に status と error code を含む log を出す形にした。
- worker は `dispatch_job` の成功/失敗境界に log を追加し、既存の completed/failed JobEvent と failed debug artifact の作成順を維持した。
- log には body/payload 全体を含めず、追跡に必要な識別子と結果だけを含めた。

## 実施作業

- `apps/api/src/diopside_api/handler.py` に API request JSON log helper を追加した。
- `apps/workers/static-exporter/src/static_exporter/pipeline.py` に worker job JSON log helper を追加した。
- `tests/test_api_handler.py` に API success/error log contract test を追加した。
- `tests/test_core_pipeline.py` に worker success/error log contract test を追加した。
- `README.md` に CloudWatch JSON log の field、Logs Insights 例、調査観点を追記した。
- `tasks/do/20260529-1152-cloudwatch-json-logs.md` を作成した。

## 成果物

- `apps/api/src/diopside_api/handler.py`
- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `tests/test_api_handler.py`
- `tests/test_core_pipeline.py`
- `README.md`
- `tasks/do/20260529-1152-cloudwatch-json-logs.md`

## 検証

- `git diff --check`: 成功
- `python3 -m py_compile apps/api/src/diopside_api/handler.py apps/workers/static-exporter/src/static_exporter/pipeline.py`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_api_handler.py tests/test_core_pipeline.py`: 38 passed
- `npm test`: 55 passed
- `npm run verify`: 成功

## fit 評価

- API/worker の success/error path に JSON log を追加し、P2-06 の field 要件と調査性の要件を満たした。
- secret や payload 全体を log しない方針を README と test で確認できる形にした。

## 未対応・制約・リスク

- 実 AWS CloudWatch Logs への出力と Logs Insights での検索は未実施。
- 既存の failed debug artifact は payload を保存する挙動のまま維持している。今回の CloudWatch log には payload 全体を含めていない。
