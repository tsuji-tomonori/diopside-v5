# StaticExport history item

## 背景

`.workspace/plan-20260530.txt` は v0.4 DDB item schema への準拠を検収基準に戻す方針を示している。
v0.4 の `StaticExport` は `pk=EXPORT#public`, `sk=VERSION#{exported_at}` に public data export の履歴を保存する設計だが、現状は `/data/latest-manifest.json` を出力するだけで DDB 履歴 item がない。

## 目的

static export 実行時に `StaticExport` history item を保存し、export_version、manifest、件数、schema versions、content hash、publish state を repository contract として追跡できるようにする。

## タスク種別

機能追加

## スコープ

- repository に `StaticExport` item type、writer、list path を追加する。
- static exporter が manifest 生成後に `StaticExport` item を保存する。
- static export job では `generated_job_id` と upload 件数を記録する。
- repository / static exporter tests、README、traceability、DDB audit を更新する。

## 対象外

- StaticExport 履歴を管理 API / UI で表示する機能。
- 既存 export 履歴の backfill。
- `publish_state=superseded` への過去 export 更新。

## 受け入れ条件

- [x] `StaticExport` item が `pk=EXPORT#public`, `sk=VERSION#{exported_at}` で保存される。
- [x] item に `export_id`、`exported_at`、`reason`、`manifest_s3_uri`、`public_prefix`、`video_count`、`tag_count`、`schema_versions`、`content_hash`、`publish_state` が含まれる。
- [x] static export job 実行時は `generated_job_id` と `uploaded_object_count` が記録される。
- [x] repository から最新順で `StaticExport` を list できる。
- [x] README、traceability、DDB schema audit が更新される。
- [x] targeted tests、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [x] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. repository に `record_static_export` / `list_static_exports` と item helper を追加する。
2. static exporter の manifest 生成後と Lambda job 完了時に StaticExport を記録する。
3. repository / static exporter tests を追加する。
4. README、traceability、DDB audit、compliance audit を更新する。
5. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/handler.py`
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py tests/test_repository_schema_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- manifest checksum と StaticExport `content_hash` が一致すること。
- manifest を publish する前の失敗を published として記録しないこと。
- 実 S3 bucket がある場合は `manifest_s3_uri` が S3 URI になること。

## リスク

- 既存 export 履歴の backfill は行わない。
- 過去 export の `superseded` 更新は後続対象。

## 完了結果

- 実装 commit: `35af7af` (`✨ feat(worker): StaticExport履歴を記録`)
- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/40
- PR 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581626169
- PR セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581626167
- 作業レポート: `reports/working/20260530-1315-static-export-history-item-report.md`

### 検証結果

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/handler.py`: pass
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py tests/test_repository_schema_contract.py`: pass（16 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（105 tests + build/package/local e2e）

### 後続対象

- 既存 export 履歴の backfill。
- StaticExport 履歴の管理 API / UI 表示。
- 過去 export を `superseded` に更新する処理。
- 実 S3 upload / 実 DynamoDB 書き込み経路確認。

## 状態

done
