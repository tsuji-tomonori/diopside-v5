# Lambda Function URLの公開面整理 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づき、main を pull してから継続作業する。
- P2-02「Lambda Function URLの公開面整理」として、管理APIをCloudFront経由に統一し、Function URLを直接使う場合は用途をREADMEで明確化する。

## 要件整理

- 利用者向け API endpoint は CloudFront `/api/*` に統一する。
- Lambda Function URL は public unauthenticated endpoint にせず、CloudFront origin 専用として扱う。
- template contract test で Function URL の `AWS_IAM`、Lambda OAC、CloudFront principal、SourceArn 制約を検証する。

## 検討・判断

- AWS公式ドキュメントで CloudFront OAC が Lambda Function URL origin に対応していることを確認し、S3 OAC とは別に Lambda URL 用 OAC を追加した。
- Function URL 自体は CloudFront origin として必要なため残すが、`AuthType: AWS_IAM` と CloudFront OAC で直接匿名呼び出しを不可にした。
- Output は利用者向けの `ApiEndpoint` を維持し、Function URL は `ApiFunctionUrlOrigin` として internal origin 用であることを明記した。

## 実施作業

- `ApiFunctionUrlOac` を追加し、`OriginAccessControlOriginType: lambda`、`SigningBehavior: always`、`SigningProtocol: sigv4` を設定。
- `ApiFunctionUrl` を `AuthType: AWS_IAM` に変更。
- `ApiFunctionUrlPermission` を `cloudfront.amazonaws.com`、`FunctionUrlAuthType: AWS_IAM`、`InvokedViaFunctionUrl: true`、対象 distribution `SourceArn` に限定。
- CloudFront の `api-function-url` origin に `ApiFunctionUrlOac` を設定。
- `ApiFunctionUrl` output を `ApiFunctionUrlOrigin` に改名し、internal origin 用の説明を追加。
- CloudFormation contract test で Function URL の公開面境界を検証。
- README に API は CloudFront `ApiEndpoint` 経由で利用し、Function URL は直接呼ばないことを明記。

## 成果物

- CloudFront 経由に統一した API origin 構成。
- Function URL 直接匿名公開の削除。
- 作業 task: `tasks/done/20260529-1117-function-url-cloudfront-only.md`

## 検証

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py`: 6 passed
- `npm test`: 43 passed
- `npm run verify`: 成功

## fit 評価

- P2-02 の「管理APIをCloudFront経由に統一」は、Function URLをCloudFront OAC付き internal origin とし、利用者向け output を CloudFront `ApiEndpoint` に限定することで満たした。
- Function URL を直接使う用途は残しておらず、README では直接呼ばない internal origin と明記した。

## 未対応・制約・リスク

- 実 CloudFront / AWS 環境への deploy と `npm run smoke:post-deploy` は、対象 URL と認証情報が必要なため未実行。
- 既存 stack へ適用する場合、Function URL auth type と Lambda permission の置換が発生する可能性がある。
