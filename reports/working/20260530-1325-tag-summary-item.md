# TagSummary item 作業レポート

## 指示

- `.workspace/plan-20260530.txt` の v0.4 設計準拠対応を継続する。
- Worktree Task PR Flow に従い、task md、検証、レポート、PR 反映まで進める。

## 要件整理

- v0.4 の `TagSummary` item を `pk=TAG#{tag_id}`, `sk=META` で保存する。
- `put_video` / `update_video_tags` で tag 件数、latest video、public visibility を再計算する。
- `list_tags`、`GET /api/tags`、static export の tag list は保存済み read model を優先する。
- video_count が 0 になった tag は public list から除外する。
- 管理 UI での category/sort order 編集、既存 data backfill、`VideoTagLink` 全面移行は対象外。

## 実施作業

- repository に `TagSummary` item type、`tag_id_for_label`、`rebuild_tag_summaries` を追加した。
- `put_video` の tag index 更新後に、変更対象 tag の `TagSummary` を再計算するようにした。
- `MemoryRepository` / `DynamoRepository` の `list_tags` が `TagSummary` を優先し、保存済み summary がない場合のみ動的 fallback するようにした。
- stale tag は `public_visible=false` として残し、public tag list から除外する contract test を追加した。
- static export の tag payload が public visible な summary を返すことを確認する test を追加した。
- README、traceability matrix、DDB schema audit、v0.4 compliance audit を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `tests/test_repository_schema_contract.py`
- `tests/test_static_exporter.py`
- `README.md`
- `docs/design/traceability-matrix.md`
- `docs/design/dynamodb-schema-audit.md`
- `reports/audit/design-v0.4-compliance-20260530.md`
- `tasks/do/20260530-1322-tag-summary-item.md`

## 検証

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_repository_schema_contract.py tests/test_api_handler.py tests/test_static_exporter.py`: pass、42 tests
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass、106 tests + build + package + local e2e

## Fit 評価

- `TagSummary` の保存、更新、public tag list での優先利用、stale tag 非表示は受け入れ条件に合致している。
- API と static export は既存の `repository.list_tags()` 経由のため、read model 優先へ追従している。

## 未対応・制約・リスク

- 既存 DynamoDB data に対する `TagSummary` backfill job は未実装。
- tag category / sort order を管理 UI から編集する機能は未実装。
- v0.4 の `VideoTagLink` key shape への全面移行は未実装。
