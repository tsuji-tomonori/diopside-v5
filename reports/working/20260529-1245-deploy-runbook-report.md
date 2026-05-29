# deploy runbook整備 作業レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づいて作業する。
- `main` から pull してから、P2-10 deploy runbook を進める。
- リポジトリの Worktree Task PR Flow に従い、task、検証、PR コメントまで行う。

## 要件整理

- README に初回 deploy、更新 deploy、rollback、static export 再実行、CloudFront cache 確認の手順を追加する。
- 実 AWS 操作は実施済みとして書かない。
- 既存の CloudFormation output、管理 API、post-deploy smoke と整合するコマンド例にする。

## 検討・判断

- rollback しやすいように、deploy artifact は固定 key ではなく release id 付き key を推奨する形にした。
- `static_export` 再実行は CloudFront 経由の管理 API とし、Function URL 直叩きの手順は追加しなかった。
- CloudFront cache 確認は `/api/*`、manifest、versioned public data、default route の header 確認と、緊急時の限定 invalidation に絞った。

## 実施作業

- README の手動 deploy 例を release id 付き artifact key に更新した。
- README に `deploy runbook` 節を追加した。
- 初回 deploy、更新 deploy、rollback、static export 再実行、CloudFront cache 確認の手順を追記した。
- P2-10 の task md を作成した。

## 成果物

- `README.md`
- `tasks/do/20260529-1245-deploy-runbook.md`

## 検証

- `git diff --check`: 成功
- `npm test`: 59 passed

## fit 評価

- plan P2-10 の要求する 5 種類の運用手順を README に追加した。
- 実 AWS deploy、rollback、static export 再実行、CloudFront cache 確認は実施していないため、README とレポートに未実施として明記した。

## 未対応・制約・リスク

- 実 AWS 環境での deploy/rollback/static export/CloudFront cache 確認は未実施。
- runbook は既存の CloudFormation template と API 契約に基づく手順であり、AWS account 固有の権限、bucket 名、token 管理手順は運用側で補完が必要。
- GitHub Apps による PR 作成・コメントが利用できない場合は、リポジトリルールに沿って理由を明記し `gh` fallback を使う。
