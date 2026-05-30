# FR-YT-010 duplicate message audit

状態: do

## 背景

`docs/design/traceability-matrix.md` の `FR-YT-010` は「重複メッセージを除外する」が `要追加監査` のまま残っている。実装とテストの証跡を確認し、現状の判定を明確にする必要がある。

## 目的

チャット重複除外の実装・テスト証跡を確認し、traceability と audit に現状を反映する。

## タスク種別

設計準拠監査

## スコープ

- `apps/shared/src/diopside_core/artifacts.py` と worker pipeline の重複除外経路を確認する。
- 該当テストを確認し、不足があれば最小テストを追加する。
- `FR-YT-010` の status と証跡を更新する。
- 作業レポートを残す。

## 受け入れ条件

- `FR-YT-010` が `要追加監査` のまま放置されない。
- 実装ファイルとテストが traceability に明記される。
- 未確認の経路は実装済み扱いせず、必要なら部分実装として残す。
- docs consistency、diff check、`npm run verify` が pass する。

## 検証計画

- `node tools/check-docs-consistency.mjs`
- 対象 pytest（必要に応じて）
- `git diff --check`
- `npm run verify`
