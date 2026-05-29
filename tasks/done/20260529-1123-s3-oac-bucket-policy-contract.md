# S3 bucket policy / OAC検証

状態: done

## 背景

`.workspace/plan-20260529.txt` の P2-03 に従い、WebBucket / PublicDataBucket が CloudFront OAC 以外から読めないことを template contract test で検証する。

## 受け入れ条件

- `WebBucket` と `PublicDataBucket` が `PublicAccessBlockConfiguration` で public ACL / policy をブロックしている。
- CloudFront S3 origin が S3 REST origin (`RegionalDomainName`) と S3 用 OAC を使い、website endpoint を使っていない。
- S3 用 OAC が `OriginAccessControlOriginType: s3`、`SigningBehavior: always`、`SigningProtocol: sigv4` である。
- `WebBucketPolicy` と `PublicDataBucketPolicy` が `cloudfront.amazonaws.com` principal の `s3:GetObject` のみを許可する。
- bucket policy が対象 CloudFront distribution ARN の `AWS:SourceArn` 条件を必須にしている。
- bucket policy に public principal (`*`) や broad read allow がないことを contract test で検証する。
- README に Web/PublicData S3 は CloudFront OAC 経由のみ読めることを明記する。
- 変更範囲に見合う検証と `npm run verify` が成功する。
