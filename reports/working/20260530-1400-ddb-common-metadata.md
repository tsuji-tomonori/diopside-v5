# DDB common metadata 作業レポート

## 指示

- `.workspace/plan-20260530.txt` の v0.4 設計準拠対応を継続する。
- main を pull してから、Worktree Task PR Flow に従い task md、実装、検証、レポート、PR 反映まで進める。

## 要件整理

- repository writer 境界で `schema_version`、`entity_id`、`created_at`、`updated_at` を付与する。
- 明示された `schema_version` / `entity_id` と既存 item の `created_at` は上書きしない。
- Memory と DynamoDB adapter の writer 経路を同じ正規化に寄せる。
- 既存 DynamoDB data の backfill、v0.4 key prefix 移行、item type ごとの詳細 schema version 設計は対象外。

## 実施作業

- root `main` で `git pull --ff-only` を実行し、`Already up to date` を確認した。
- repository に `item_schema_version`、`item_entity_id`、`normalize_item_metadata` を追加した。
- `MemoryRepository.put_item` と `DynamoRepository.put_item` が共通 metadata 正規化を通るようにした。
- `DynamoRepository.create_job` の条件付き put でも正規化済み `Job` item を保存するようにした。
- `created_at` の保持、明示 metadata の保持、default metadata 付与を contract test で固定した。
- README、DDB schema audit、compliance audit を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `tests/test_repository_schema_contract.py`
- `README.md`
- `docs/design/dynamodb-schema-audit.md`
- `reports/audit/design-v0.4-compliance-20260530.md`
- `tasks/do/20260530-1357-ddb-common-metadata.md`

## 検証

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`: pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`: pass、14 tests
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass、115 tests + build + package + local e2e

## Fit 評価

- 総合fit: 4.5 / 5.0
- common metadata の付与・保持は repository writer 境界で満たした。
- item type ごとの詳細 schema version 命名と既存 data backfill は未対応のため、v0.4 完全準拠ではなく段階的な部分準拠である。

## 未対応・制約・リスク

- 既存 DynamoDB data に対する common metadata backfill は未実装。
- `schema_version` は `ddb-{item_type}-v1` の default であり、item type ごとの詳細 schema version 設計は後続対象。
- 実 DynamoDB 上での書き込み確認は未実施。local contract と repository tests で検証した。
