# PR コメントに基づく post-deploy smoke 補強

## 受けた指示

- PR のコメントをもとに修正する。

## 要件整理

- PR #2 の reviewThreads と inline review comments は 0 件だった。
- top-level comment のセルフレビューに残っていた deploy 後 suggestion を、実行可能な確認手順へ落とし込む。
- 実施していない本番 deploy や実 AWS smoke は実施済み扱いにしない。

## 検討・判断

- post-deploy 確認は `DIOPSIDE_E2E_BASE_URL` を受け取る npm script として追加した。
- public data は一時 directory に取得し、既存の `tools/check-public-contract.mjs` を再利用して exporter contract と同じ観点で検証する。
- 管理 API は token/CSRF がある場合だけ実行し、ない場合は明示的に skip する。
- 実デプロイ環境はこの作業では利用していないため、README に実行手順として明記した。

## 実施作業

- `tools/run-post-deploy-smoke.mjs` を追加し、CloudFront/public API/public data/admin API の post-deploy smoke を実装した。
- `npm run smoke:post-deploy` を追加した。
- `npm test` に post-deploy smoke script の構文チェックを追加した。
- README に deploy 後の smoke 実行手順と確認観点を追記した。
- 作業 task を `tasks/do/` に追加した。

## 成果物

- `tools/run-post-deploy-smoke.mjs`
- `package.json`
- `README.md`
- `tasks/do/20260528-1544-pr-comment-post-deploy-smoke.md`

## 検証

- `npm test`: 成功。18 tests passed。
- `npm run verify`: 成功。
- `git diff --check`: 成功。

## fit 評価

- PR コメント上の deploy 後 suggestion は、手順だけでなく再実行可能な smoke script として反映できた。
- 実 AWS 環境での `npm run smoke:post-deploy` は、deploy 後に base URL と admin credential を指定して実行する前提として残る。

## 未対応・制約・リスク

- 実 AWS deploy と実 CloudFront に対する smoke は未実施。
- GitHub Actions checks は PR に存在しないため未確認。
