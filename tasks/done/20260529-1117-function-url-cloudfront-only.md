# Lambda Function URLの公開面整理

状態: done

## 背景

`.workspace/plan-20260529.txt` の P2-02 に従い、管理APIをCloudFront経由へ統一し、Lambda Function URLを直接公開する用途をなくす。直接使う必要が残る場合はREADMEで用途を明確化する。

## 受け入れ条件

- Lambda Function URL は `AuthType: AWS_IAM` とし、public unauthenticated invoke (`AuthType: NONE` / `Principal: "*"`) を使わない。
- CloudFront の Lambda Function URL origin には Lambda 用 OAC を設定し、CloudFront が SigV4 で origin を呼ぶ構成にする。
- Lambda permission は CloudFront service principal、対象 distribution ARN、Function URL 経由に限定する。
- `ApiEndpoint` は CloudFront `/api` を唯一の利用者向けAPI endpointとして出力する。
- `ApiFunctionUrl` output は削除するか、直接利用不可の内部 origin であることが明確な名前・説明にする。
- CloudFormation contract test が上記の公開面境界を検証する。
- README に API は CloudFront 経由で利用し、Function URL は CloudFront origin 専用で直接呼ばないことを明記する。
- 変更範囲に見合う検証と `npm run verify` が成功する。
