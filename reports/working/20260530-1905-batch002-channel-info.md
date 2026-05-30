# BATCH-002 チャンネル情報取得 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と v0.4 設計書に沿って、設計準拠差分を継続的に潰す。
- `BATCH-002` が `要追加監査` のまま残っているため、実装・テスト証跡を確認して必要な対応を行う。

## 要件整理

- metadata sync は uploads playlist / videos 取得だけでなく、対象 channel の基本情報を取得して `Channel` / `ChannelRef` に保存する必要がある。
- local test では YouTube 実 API を呼ばず、fake client で `channels.list` 相当の response を渡して検証する。

## 実施作業

- `apps/shared/src/diopside_core/youtube.py` に `YouTubeClient.channels` と `normalize_channel_resource` を追加した。
- `metadata_sync` が channel ID を持つ場合に `channels.list` を呼び、raw response を `raw/youtube/metadata/channel_id={channel_id}/channels/` へ保存し、`repo.put_channel` で `Channel` / `ChannelRef` を更新するようにした。
- `channels.list` quota usage を記録するようにした。
- `tests/test_core_pipeline.py` の metadata sync fake client と検証を更新し、channel 情報取得、raw 保存、quota usage、cursor/video 保存を同一 flow で確認した。
- `docs/design/traceability-matrix.md` の `BATCH-002` を `実装済` に更新した。
- `reports/audit/design-v0.4-compliance-20260530.md` に BATCH-002 の対応内容を追記した。

## 成果物

- metadata sync が channel 基本情報を取得し、DynamoDB read model 相当の `Channel` / `ChannelRef` を更新する。
- `BATCH-002` は `要追加監査` から `実装済` に更新された。

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_metadata_sync_paginates_saves_raw_and_cursor tests/test_core_pipeline.py::test_metadata_sync_resumes_from_channel_cursor tests/test_repository_schema_contract.py::test_repository_writes_channel_ref_and_lists_channels_from_read_model`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（135 tests、build、package:deploy、local e2e）

## fit 評価

- v0.4 の channel 情報取得を、既存 metadata sync / repository 境界に沿って追加した。
- YouTube 実 API 呼び出しは test では発生しない。

## 未対応・制約・リスク

- 既存 channel data の backfill は未対応。
- `channels.list` が失敗した場合の graceful fallback は未追加で、metadata sync job 全体の失敗として扱う。
