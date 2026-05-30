# RandomBucket random videos API work report

## 受けた指示

- `.workspace/plan-20260530.txt` に沿って、v0.4 基本設計へ実装を寄せる。
- main を pull してから、専用 worktree / PR branch で task md、実装、検証、レポート、PR 更新まで進める。

## 要件整理

- v0.4 の `RandomBucket` は `pk=RANDOM#DEFAULT`, `sk=VID#{bucket_no}#{video_id}` の事前シャッフル bucket。
- `/api/random-videos` は RandomBucket を利用し、`count` / `seed` / `tag` / `year` でランダム動画を返す。
- 現状は公開動画一覧を時刻で rotate するだけで、RandomBucket item がなかった。

## 検討・判断

- 既存の `put_video` 経路に RandomBucket upsert を追加し、公開動画が保存されるたびに random API 用の item を更新する形にした。
- `bucket_no` は `video_id` の sha256 から deterministic に算出し、既存動画の再保存でも安定するようにした。
- 既存データ backfill と専用 rebuild job は大きくなるため後続対象とし、RandomBucket が空の環境では公開動画一覧 fallback を残した。

## 実施作業

- `RandomBucket` を repository allowlist に追加した。
- `random_bucket_item`、`list_random_videos`、`put_video` 時の RandomBucket upsert / 非公開時 stale 削除を追加した。
- DynamoRepository で `RANDOM#DEFAULT` query path を追加した。
- `/api/random-videos` を `count` / `seed` / `tag` / `year` に対応し、seed による安定順序に変更した。
- API / repository schema contract / fake Dynamo table tests を更新した。
- README、traceability、DDB schema audit、v0.4 compliance audit を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `apps/api/src/diopside_api/handler.py`
- `tests/test_api_handler.py`
- `tests/test_repository_schema_contract.py`
- `tests/test_core_pipeline.py`
- `README.md`
- `docs/design/dynamodb-schema-audit.md`
- `docs/design/traceability-matrix.md`
- `reports/audit/design-v0.4-compliance-20260530.md`

## 検証

- `python3 -m py_compile apps/api/src/diopside_api/handler.py apps/shared/src/diopside_core/repository.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src python3 -m pytest tests/test_api_handler.py tests/test_repository_schema_contract.py`: pass（33 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_api_handler.py tests/test_repository_schema_contract.py`: pass（76 tests）
- `git diff --check`: pass
- `npm run verify`: pass（104 tests + build/package/local e2e）

## fit 評価

- 指示適合: 4.5 / 5
- v0.4 の RandomBucket key shape と random API の seed/count/tag/year 条件に寄せた。
- backfill / rebuild job と Video key prefix migration は対象外として残した。

## 未対応・制約・リスク

- 既存 DynamoDB data への RandomBucket backfill は未実装。
- RandomBucket 専用 rebuild job は未実装。
- 実 DynamoDB query / API Gateway 経路での random API は未検証。
