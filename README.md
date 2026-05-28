# diopside v5

`diopside` は、白雪巴 YouTube 公開アーカイブを低コストに検索・閲覧するための serverless skeleton です。設計根拠は `.workspace/diopside_basic_design_v0.4.md` です。

## 現在の実装範囲

- `apps/web`: CloudFront + S3 配信用の静的 Web UI。静的 JSON 契約を読み、最新一覧、タグ/キーワード検索、詳細、wordcloud/timestamp summary を表示します。
- `apps/api`: Lambda Function URL / API Gateway で動かす Python handler。公開 GET と、Bearer token + CSRF で保護された管理 job endpoint の契約を実装します。
- `apps/workers/static-exporter`: DynamoDB 由来の read model または fixture から public JSON を生成する worker skeleton です。
- `infra/cloudformation`: S3、DynamoDB、SQS、Lambda、Function URL を作る CloudFormation template です。
- `data/fixtures`: ローカル検証用 fixture。本番経路の fallback としては使いません。

## ローカル検証

```sh
npm test
npm run build
npm run package:deploy
npm run e2e:local
```

`npm run verify` で上記をまとめて実行します。

## デプロイ前成果物

`npm run package:deploy` は `build/deploy/` に次を生成します。

- `api.zip`
- `static-exporter.zip`
- `diopside.yaml`

実 AWS へのデプロイは人が実行します。例:

```sh
aws s3 cp build/deploy/api.zip s3://<artifact-bucket>/diopside/api.zip
aws s3 cp build/deploy/static-exporter.zip s3://<artifact-bucket>/diopside/static-exporter.zip

aws cloudformation deploy \
  --template-file build/deploy/diopside.yaml \
  --stack-name diopside-prod \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    EnvName=prod \
    AdminToken=<token> \
    AdminCsrfToken=<csrf-token> \
    LambdaArtifactBucket=<artifact-bucket> \
    ApiCodeS3Key=diopside/api.zip \
    StaticExporterCodeS3Key=diopside/static-exporter.zip
```

スタック作成後は、公開 UI と初期 public data を各 bucket に同期します。

```sh
npm run build
aws s3 sync build/web s3://<web-bucket>/
aws s3 sync build/web/data s3://<public-data-bucket>/data/
```

## デプロイ後 e2e

デプロイ後、CloudFront domain または Function URL を指定して e2e を実行します。

```sh
DIOPSIDE_E2E_BASE_URL=https://<cloudfront-domain> npm run e2e:local
```

現時点では外部デプロイ、YouTube API 実取得、CloudFront 経由 e2e は未実施です。
