# GitHub Actions CI追加

状態: do

## 背景

`.workspace/plan-20260529.txt` の P4-01 に従い、PR で `npm run verify`、CloudFormation parse/contract、public contract、unit tests が実行される GitHub Actions CI を追加する。

## 目的

PR ごとに本 repository の主要検証を自動実行し、CloudFormation contract、public data contract、unit tests、build/package/local e2e を確認できる状態にする。

## タスク種別

CI 追加

## スコープ

- `.github/workflows/ci.yml`

## 計画

1. 既存 npm scripts と必要 runtime を確認する。
2. Node 22 / Python 3.13 / Chrome を使う GitHub Actions workflow を追加する。
3. `npm ci` と `npm run verify` を実行する job にする。
4. 検証、作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

CI 設定追加であり README 更新は不要。workflow の内容と検証は作業レポートに残す。

## 受け入れ条件

- PR で GitHub Actions CI が実行される。
- CI で `npm run verify` が実行される。
- CI で CloudFormation parse/contract が実行される。
- CI で public contract が実行される。
- CI で unit tests が実行される。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- `npm test`
- `npm run verify`

## リスク

- GitHub Actions 上の実行は PR 作成後の外部 CI に依存するため、この作業中は workflow 定義と local verify で確認する。
