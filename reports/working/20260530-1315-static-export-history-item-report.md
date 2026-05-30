# StaticExport history item work report

## 受けた指示

- `.workspace/plan-20260530.txt` に沿って、v0.4 基本設計へ実装を寄せる。
- main を pull してから、専用 worktree / PR branch で task md、実装、検証、レポート、PR 更新まで進める。

## 要件整理

- v0.4 の `StaticExport` は `pk=EXPORT#public`, `sk=VERSION#{exported_at}` で public data export 履歴を保存する。
- 既存実装は manifest JSON を出力するが、DynamoDB に export 履歴を残していなかった。
- static export job の成功時に job id、upload 件数、manifest URI、content hash を追跡できる必要がある。

## 検討・判断

- `StaticExport` writer/list を repository に追加し、`static_export` job が manifest 生成・publish 成功後に記録する形にした。
- `content_hash` は manifest の `STATIC-006.checksum_sha256` と一致させた。
- S3 bucket が設定されている場合は `manifest_s3_uri` を `s3://.../latest-manifest.json` にし、local 実行では `local://latest-manifest.json` として実環境未使用であることを明示した。

## 実施作業

- `StaticExport` を repository allowlist に追加した。
- `static_export_item`、`record_static_export`、`list_static_exports` を追加した。
- static exporter Lambda job 成功時に `StaticExport` history item を保存するようにした。
- repository / static exporter tests を追加した。
- README、traceability、DDB schema audit、v0.4 compliance audit を更新した。

## 成果物

- `apps/shared/src/diopside_core/repository.py`
- `apps/workers/static-exporter/src/static_exporter/handler.py`
- `tests/test_repository_schema_contract.py`
- `tests/test_static_exporter.py`
- `README.md`
- `docs/design/dynamodb-schema-audit.md`
- `docs/design/traceability-matrix.md`
- `reports/audit/design-v0.4-compliance-20260530.md`

## 検証

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/handler.py`: pass
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py tests/test_repository_schema_contract.py`: pass（16 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（105 tests + build/package/local e2e）

## fit 評価

- 指示適合: 4.5 / 5
- v0.4 の StaticExport key shape と必須属性を repository contract と static export job に追加した。
- 管理 API/UI 表示、既存履歴 backfill、superseded 更新は後続対象として残した。

## 未対応・制約・リスク

- 既存 export 履歴の backfill は未実装。
- StaticExport 履歴の管理 API / UI 表示は未実装。
- 過去 export を `superseded` に更新する処理は未実装。
- 実 S3 upload / 実 DynamoDB 書き込み経路での StaticExport item は未検証。
