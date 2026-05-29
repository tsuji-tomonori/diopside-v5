# CloudFront behavior検証

状態: done

## 背景

`.workspace/plan-20260529.txt` の P2-01 に従い、CloudFront で `/`、`/assets/*`、`/data/latest-manifest.json`、`/data/v/*`、`/api/*` が想定 origin/cache へ流れることを template contract と post-deploy smoke で検証する。

## 受け入れ条件

- CloudFormation contract test が CloudFront behavior の順序を `/api/*`、`/data/latest-manifest.json`、`/data/v/*`、`/assets/*` として検証する。
- contract test が `/api/*` は `api-function-url` origin、no-store cache、全HTTP method許可であることを検証する。
- contract test が `/data/latest-manifest.json` は `public-data-s3` origin、短TTL cacheであることを検証する。
- contract test が `/data/v/*` は `public-data-s3` origin、immutable cacheであることを検証する。
- contract test が `/assets/*` と default behavior は `web-s3` origin、immutable cacheであることを検証する。
- post-deploy smoke が `/`、`/assets/*`、`/data/latest-manifest.json`、`/data/v/*`、`/api/*` を CloudFront 経由で取得し、主要 cache/header 期待を確認する。
- README に CloudFront behavior 検証観点を反映する。
- 変更範囲に見合う検証と `npm run verify` が成功する。
