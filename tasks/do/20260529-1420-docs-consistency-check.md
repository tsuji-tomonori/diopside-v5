# docs consistency check

状態: do

## 背景

`.workspace/plan-20260529.txt` の P4-07 に従い、README と設計書で実装済み job/API/path/schema が一致していることをチェックできるようにする。

## 目的

実装済みの API route、管理 job、worker job、public data path、schema_version が README からずれた場合に CI で検出できる状態にする。

## タスク種別

ドキュメント更新

## スコープ

- `README.md`
- `tools/check-docs-consistency.mjs`
- `package.json`

## 計画

1. API handler、worker pipeline、static exporter、chat schema の実装済み契約を確認する。
2. README に実装済み API route と response schema、worker job、public data schema の対応表を追加・調整する。
3. docs consistency check を追加し、README と実装済み契約のずれを検出する。
4. `.workspace/diopside_basic_design_v0.4.md` は gitignore 対象のため、ローカル検証では環境変数指定時に補助的に確認し、CI では tracked README を正とする。
5. `npm test` と `npm run verify` に含まれることを確認する。
6. 作業レポート、commit、PR、受け入れ条件コメント、セルフレビューまで完了する。

## ドキュメント保守方針

P4-07 自体が docs consistency の改善であるため、README を durable doc として更新する。`docs/` はこのリポジトリでは未配置のため、新規 docs 分割は行わない。

## 受け入れ条件

- README に実装済み public API / admin API route が記載され、検証で漏れを検出できる。
- README に実装済み管理 job API と worker job type が記載され、検証で漏れを検出できる。
- README に実装済み public data path と schema_version が記載され、検証で漏れを検出できる。
- normalized chat schema の必須 key と schema_version が README と実装で一致していることを検証できる。
- `.workspace/diopside_basic_design_v0.4.md` を指定したローカル検証で、主要設計前提が確認できる。
- docs consistency check が `npm test`、ひいては CI の `npm run verify` で実行される。
- 変更範囲に見合う検証が成功する。

## 検証計画

- `git diff --check`
- `node tools/check-docs-consistency.mjs`
- `DIOPSIDE_DESIGN_DOC=/home/t-tsuji/project/diopside-v5/.workspace/diopside_basic_design_v0.4.md node tools/check-docs-consistency.mjs`
- `npm test`
- `npm run verify`

## PR review points

- README の追加表が実装済み契約に限定され、未実装 route を実装済みとして書いていないこと。
- `.workspace` の設計書を CI 前提にせず、tracked file の検証を CI に載せていること。
- RAG、認可境界、benchmark 固有値には影響しないこと。

## リスク

- `.workspace` は gitignore 対象のため、GitHub Actions 上では設計書本文の直接検証は行わない。設計書由来の主要前提は README と script の contract に落とし込む。
