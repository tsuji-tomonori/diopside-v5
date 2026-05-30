# ADMIN-SESSION traceability 整合

状態: do

## 背景

ADMIN-SESSION は HttpOnly cookie + CSRF と管理 UI session flow が実装済みで、audit でも P0-05 は対応済みになっている。一方で `docs/design/traceability-matrix.md` の `NFR-SEC-005` が古い `差分あり` のまま残っており、設計準拠表と実装・検証状況が一致していない。

## 目的

`NFR-SEC-005` の implementation/test/status を現状に合わせ、管理操作保護が cookie session + CSRF 経路で検証されていることを traceability に反映する。

## タスク種別

ドキュメント整合

## スコープ

- `docs/design/traceability-matrix.md` の `NFR-SEC-005` を更新する。
- 必要に応じて audit/report に補足する。
- 作業レポートを残す。

## 受け入れ条件

- `NFR-SEC-005` が ADMIN-SESSION 実装済みの現状と矛盾しない。
- implementation files に API handler と public UI が含まれる。
- tests に管理 session/CSRF を検証する API test と local e2e が含まれる。
- 未実施検証を実施済みとして書かない。
- docs consistency と `npm run verify` が pass する。

## 検証計画

- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`
