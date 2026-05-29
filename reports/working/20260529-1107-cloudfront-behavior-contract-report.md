# CloudFront behavior検証 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づき、main を pull してから継続作業する。
- P2-01「CloudFront behavior検証」として、`/`、`/assets/*`、`/data/latest-manifest.json`、`/data/v/*`、`/api/*` が想定 origin/cache へ流れることを post-deploy smoke で確認できるようにする。

## 要件整理

- CloudFormation template の ordered behavior 順序、origin、cache policy を静的 contract test で確認する。
- post-deploy smoke は CloudFront 経由で web root、asset、manifest、versioned data、API を取得し、SPA fallback や Function URL 直叩きではないことを検出する。
- API は origin response の `cache-control: no-store, no-cache, max-age=0` を維持していることを確認する。

## 検討・判断

- CloudFront の cache policy は response header そのものを必ず書き換えるものではないため、TTL/cache policy の厳密検証は CloudFormation contract test で行うことにした。
- post-deploy smoke では `via` / `x-cache` を確認し、CloudFront 経由ではない URL を検出するようにした。
- `/assets/*` は実ファイル `assets/placeholder-thumbnail.svg` を取得して確認する。

## 実施作業

- `tests/test_cloudformation_contract.py` に CloudFront ordered behavior、origin、cache policy、allowed/cached methods、TTL の構造検証を追加。
- `tools/run-post-deploy-smoke.mjs` に `/`、`/assets/placeholder-thumbnail.svg`、`/api/health`、`/data/latest-manifest.json`、versioned public data の CloudFront header 確認を追加。
- `/api/health` の no-store/no-cache/max-age=0 header 確認を追加。
- README に CloudFront behavior の順序・検証観点を追記。

## 成果物

- CloudFront behavior contract test の強化。
- post-deploy smoke の CloudFront 経由確認追加。
- 作業 task: `tasks/done/20260529-1107-cloudfront-behavior-contract.md`

## 検証

- `git diff --check`: 成功
- `node --check tools/run-post-deploy-smoke.mjs`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py`: 5 passed
- `npm test`: 42 passed
- `npm run verify`: 成功

## fit 評価

- `/api/*`、`/data/latest-manifest.json`、`/data/v/*`、`/assets/*`、default web behavior の origin/cache policy は template contract test で検証される。
- post-deploy smoke は CloudFront 経由 header と実データ/API取得で経路を確認する。

## 未対応・制約・リスク

- 実 CloudFront / AWS 環境に対する `npm run smoke:post-deploy` は、対象 URL と認証情報が必要なため未実行。
- S3 object の `Cache-Control` metadata は今回の範囲では変更していない。CloudFront cache policy の TTL は template contract で検証している。
