# VideoMonthIndex read model 作業レポート

## 指示

- `.workspace/plan-20260530.txt` の v0.4 設計準拠対応を継続する。
- main を pull してから、Worktree Task PR Flow に従い task md、実装、検証、レポート、PR 反映まで進める。

## 要件整理

- v0.4 の `VideoMonthIndex` item を `pk=VID#{video_id}`, `sk=INDEX#MONTH#{yyyyMM}` で保存する。
- 公開動画保存時に月別 index を更新し、非公開化または公開月変更時に stale index を削除する。
- archive calendar API と static export の calendar 生成は、repository の月別 read model を優先利用する。
- 既存 DynamoDB data の backfill、`Video` key prefix の全面移行、Calendar UI 新規実装は対象外。

## 実施作業

- root `main` で `git pull --ff-only` を実行し、`Already up to date` を確認した。
- `VideoMonthIndex` item type、`video_month_key`、`video_month_index_item`、`list_video_month_indexes` を repository に追加した。
- `put_video` が公開動画の `VideoMonthIndex` を upsert し、月変更・非公開化時に stale index を削除するようにした。
- DynamoDB repository では `by_public_date` GSI の `VIDEO#MONTH#{yyyyMM}` query path を追加し、未 backfill 環境では公開動画一覧 fallback を維持した。
- `GET /api/archive-calendar` の repository 経路と static exporter の calendar 生成を `VideoMonthIndex` 優先に変更した。
- repository/API/static exporter tests を追加し、README、traceability matrix、DDB schema audit、compliance audit を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `apps/api/src/diopside_api/handler.py`
- `apps/workers/static-exporter/src/static_exporter/handler.py`
- `tests/test_repository_schema_contract.py`
- `tests/test_api_handler.py`
- `tests/test_static_exporter.py`
- `README.md`
- `docs/design/traceability-matrix.md`
- `docs/design/dynamodb-schema-audit.md`
- `reports/audit/design-v0.4-compliance-20260530.md`
- `tasks/do/20260530-1331-video-month-index.md`

## 検証

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/api/src/diopside_api/handler.py apps/workers/static-exporter/src/static_exporter/handler.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_repository_schema_contract.py tests/test_api_handler.py tests/test_static_exporter.py`: pass、44 tests
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass、108 tests + build + package + local e2e

## Fit 評価

- 総合fit: 4.6 / 5.0
- `VideoMonthIndex` の保存、stale 削除、archive calendar API/static export の read model 優先利用は満たした。
- 既存 data backfill と v0.4 key prefix の全面移行は対象外として明示したため、v0.4 完全準拠ではなく段階的な部分準拠である。

## 未対応・制約・リスク

- 既存 DynamoDB data に対する `VideoMonthIndex` backfill job は未実装。
- `Video` item 本体は現行 `VIDEO#{video_id}` key のままで、v0.4 `VID#{video_id}` への全面移行は未実装。
- 実 DynamoDB 上での GSI query は未実施。local contract と repository tests で検証した。
