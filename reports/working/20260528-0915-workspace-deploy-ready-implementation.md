# .workspace 仕様に基づくデプロイ前実装レポート

## 受けた指示

- `.workspace` 仕様に従って実装する。
- デプロイは人が行うため、デプロイ直前まで進める。
- 残りはデプロイして e2e テストできる状態にする。

## 要件整理

| 要件ID | 要件 | 対応状況 |
|---|---|---|
| R1 | `.workspace/diopside_basic_design_v0.4.md` を根拠に低コスト serverless 構成を実装する | 対応 |
| R2 | 公開閲覧を静的 JSON と静的 UI で確認できる | 対応 |
| R3 | API の公開 GET と管理 job endpoint の基本契約を実装する | 対応 |
| R4 | デプロイ前 artifact と CloudFormation template を生成できる | 対応 |
| R5 | デプロイ後 e2e の前段としてローカル e2e を実行できる | 対応 |
| R6 | 実 AWS デプロイと CloudFront 経由 e2e は実施済み扱いにしない | 対応 |

## 検討・判断の要約

- 既存リポジトリには本体実装がなく、`.workspace/diopside_basic_design_v0.4.md` を authoritative source とした。
- 初期実装は Phase 1 相当の「デプロイ可能な skeleton」を優先し、CloudFront + S3 静的 UI、Lambda API、SQS/DynamoDB/S3 の IaC、static export worker、ローカル e2e を追加した。
- fixture は `data/fixtures/` に分離し、本番 UI の暗黙 fallback としては扱わない。デプロイ後は S3 public-data を同期または static export で更新する前提にした。
- Next.js/FastAPI/CDK の full stack 化は依存導入と実装量が大きいため、今回の到達点では依存最小の静的 UI、Python Lambda handler、CloudFormation template を選択した。

## 実施作業

- `apps/web` に静的 UI を追加し、`/data/latest-manifest.json` と versioned public JSON から最新一覧、タグ検索、動画詳細、wordcloud/timestamp summary を表示できるようにした。
- `apps/api` に Python Lambda handler を追加し、`/api/health`、`/api/config`、`/api/home`、`/api/videos`、`/api/tags`、`/api/random-videos`、動画詳細、artifact endpoint と管理 job endpoint を実装した。
- 管理 job endpoint は Bearer token と CSRF token を要求し、SQS queue 設定がある場合に enqueue、ローカル検証時のみ明示 dry-run を許可する形にした。
- `apps/workers/static-exporter` に public JSON export skeleton を追加した。
- `infra/cloudformation/diopside.yaml` に S3 bucket、DynamoDB single-table、SQS/DLQ、Lambda Function URL、worker Lambda を定義した。
- `tools/` に public contract 検証、web build、deploy artifact package、local e2e runner を追加した。
- `README.md` にローカル検証、artifact 作成、手動デプロイ、デプロイ後 e2e の手順を記載した。

## 成果物

| 成果物 | 内容 |
|---|---|
| `README.md` | 構成、検証、デプロイ前 artifact、手動デプロイ手順 |
| `apps/web/` | 静的 Web UI |
| `apps/api/` | Lambda API handler と local server |
| `apps/workers/static-exporter/` | static export worker skeleton |
| `data/fixtures/public/` | ローカル検証用 public JSON fixture |
| `infra/cloudformation/diopside.yaml` | AWS serverless stack template |
| `tools/build-web.mjs` | 静的 web build |
| `tools/check-public-contract.mjs` | public JSON 契約検証 |
| `tools/package_deploy.py` | Lambda zip と template の package |
| `tools/run-local-e2e.mjs` | ローカル/remote e2e smoke |
| `tests/` | API handler と static exporter の unit tests |

## 実行した検証

- `npm test`: pass
- `npm run build`: pass
- `npm run package:deploy`: pass
- `npm run e2e:local`: pass。初回は sandbox のローカル port bind 制約で `EPERM` になったため、ユーザー承認後に同一固定コマンドを権限付きで再実行。
- CloudFormation YAML parse check: pass
- `git diff --check`: pass

## 未実施・制約

- 実 AWS への CloudFormation deploy は未実施。ユーザー指示によりデプロイは人が行うため。
- CloudFront / S3 / Lambda Function URL 経由の実環境 e2e は未実施。デプロイ前で URL が存在しないため。
- YouTube Data API 実取得、replay chat parser の全 renderer 対応、wordcloud 画像生成は skeleton 段階であり、段階導入 Phase 2 以降の実装が必要。
- CDK/Next.js/FastAPI の full framework 実装ではなく、デプロイ前到達点として依存最小の CloudFormation、静的 UI、Python Lambda handler を採用した。

## Fit 評価

総合fit: 4.1 / 5.0（約82%）

理由: デプロイ直前までに必要な app/API/worker/infra/検証導線は揃えた。一方で、実デプロイ、実 AWS e2e、YouTube 実取得、設計書にある全 worker の本実装は未実施であり、設計全体の完全実装ではなく deployable skeleton としての到達である。
