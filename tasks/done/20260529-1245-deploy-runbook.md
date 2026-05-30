# deploy runbook整備

状態: done

## 背景

`.workspace/plan-20260529.txt` の P2-10 に従い、README に初回 deploy、更新 deploy、rollback、static export 再実行、CloudFront cache 確認の手順を追加する。

## 目的

実 AWS 環境への操作を実施せずに、運用者が安全に deploy と rollback、公開 data 再生成、CloudFront 経由確認を行える runbook を README に残す。

## タスク種別

ドキュメント更新

## スコープ

- README の deploy 手順整理
- 初回 deploy と更新 deploy の前提・コマンド・確認観点
- rollback 手順
- static export 再実行手順
- CloudFront cache 確認手順

## 計画

1. 現在の README の deploy / post-deploy e2e 節を確認する。
2. CloudFormation output、S3 sync、管理 API、smoke の既存契約に合わせて runbook を追記する。
3. README 内の既存手順と重複しすぎないように、既存 deploy 節を補強する。
4. Markdown と npm test で確認する。
5. 作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

README の運用手順として追記する。実行していない AWS 操作は実施済みとして書かず、dry-run 可能な local build/test と手動操作例を分けて記載する。

## 受け入れ条件

- README に初回 deploy の手順がある。
- README に更新 deploy の手順がある。
- README に rollback の手順がある。
- README に static export 再実行の手順がある。
- README に CloudFront cache 確認の手順がある。
- 実 AWS deploy を実施していないことが明記される。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- `npm test`

## リスク

- 実 AWS deploy、rollback、CloudFront cache、static export の実環境操作は行わないため、README の手順整合性と既存 test による検証に留まる。

## 完了記録

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/24
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/24#issuecomment-4570181118
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/24#issuecomment-4570181116
- 作業レポート: `reports/working/20260529-1245-deploy-runbook-report.md`

## 検証結果

- `git diff --check`: 成功
- `npm test`: 59 passed
