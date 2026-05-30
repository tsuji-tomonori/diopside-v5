# BATCH-002 channel info fetch

状態: do

## 背景

`docs/design/traceability-matrix.md` の `BATCH-002` は「チャンネル情報取得」が `要追加監査` のまま残っている。v0.4 の metadata sync は uploads playlist 差分だけでなく、対象 channel の基本情報を保存する必要がある。

## 目的

metadata sync 経路で channel 情報取得・保存の証跡を明確にし、必要なら実装とテストを追加して BATCH-002 を `実装済` または適切な状態に更新する。

## タスク種別

設計準拠監査・実装

## スコープ

- `apps/shared/src/diopside_core/youtube.py` の channel API helper 有無を確認する。
- `apps/workers/static-exporter/src/static_exporter/pipeline.py` の `metadata_sync` が channel 情報を保存しているか確認する。
- 不足時は channel 情報取得・保存の最小実装とテストを追加する。
- traceability、audit、作業レポートを更新する。

## 受け入れ条件

- BATCH-002 が `要追加監査` のまま残らない。
- channel 情報の取得元、保存先、テスト証跡が traceability に明記される。
- YouTube 実 API 呼び出しが local test で発生しない。
- docs consistency、targeted test、`npm run verify` が pass する。

## 検証計画

- 対象 pytest
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`
