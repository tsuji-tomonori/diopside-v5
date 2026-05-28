# .workspace 仕様に基づくデプロイ前実装

## 背景

ユーザーから「.workspace 仕様に従って実装を行って。デプロイは人が行うので、その前まで。残りデプロイしてe2eテストができる状態として。」という依頼があった。

`.workspace/diopside_basic_design_v0.4.md` は、白雪巴 YouTube 公開アーカイブ検索・閲覧・チャット解析バックエンド `diopside` の基本設計書であり、CloudFront + S3 静的配信、低コストな Lambda/SQS/DynamoDB/S3 構成、公開閲覧用静的 JSON、管理 API、worker、テスト設計を含む。

## 目的

外部デプロイそのものは実施せず、人がデプロイした後に e2e テストへ進められるよう、仕様に沿った deployable skeleton、ローカル検証、デプロイ前手順を整える。

## スコープ

- 公開 Web UI の静的アプリ基盤
- 公開 JSON 契約と fixture
- Lambda API handler の公開/管理 endpoint 基盤
- worker skeleton と static export 生成
- CloudFormation ベースの AWS リソース定義
- デプロイ前検証・ローカル e2e 導線
- README/運用手順

## タスク種別

機能追加

## 計画

1. `.workspace` 仕様から、デプロイ前に必要な最小実装範囲を抽出する。
2. monorepo の app/package/infra/test 構成を追加する。
3. 公開 UI、公開 JSON、API handler、worker、IaC を実装する。
4. デプロイ前検証コマンドとローカル e2e を追加する。
5. README と作業レポートへ、実施内容・未実施デプロイ・残るリスクを記録する。

## ドキュメント保守方針

`.workspace` 仕様自体は入力資料として変更しない。デプロイ前に必要なセットアップ、検証、残る人手作業は `README.md` と作業レポートに記録する。

## 受け入れ条件

- [x] `.workspace/diopside_basic_design_v0.4.md` の低コスト serverless 方針に沿った app/API/worker/infra 構成が追加されている。
- [x] 公開 UI が静的 JSON を読み、最新一覧・検索/タグ・詳細・wordcloud/timestamp 情報を表示できる。
- [x] API handler が公開 GET と保護された管理 job endpoint の基本契約を返せる。
- [x] 静的 export 生成と contract validation がローカルで実行できる。
- [x] AWS デプロイ前に必要な package artifact と CloudFormation template が生成できる。
- [x] デプロイ後 e2e に相当するローカル smoke/e2e 検証が実行できる。
- [x] 実施済み検証と、外部デプロイ・実 AWS e2e の未実施理由が記録されている。

## 検証計画

- `npm test`
- `npm run build`
- `npm run package:deploy`
- `npm run e2e:local`
- `git diff --check`

## PR レビュー観点

- docs と実装の同期: `.workspace` の方針、README、検証コマンドが矛盾しないこと。
- 変更範囲に見合うテスト: public contract、API route、static export、local e2e を確認すること。
- RAG の根拠性・認可境界: 本変更は RAG を含まない。管理 API の token/CSRF 境界を弱めていないこと。
- benchmark 期待語句・QA sample 固有値・dataset 固有分岐: fixture は契約検証用に分離し、本番 fallback として架空値を混入しないこと。

## リスク

- 実 AWS への deploy と CloudFront 経由 e2e はユーザー作業範囲として未実施になる。
- YouTube API 実取得、replay parser の全 renderer 対応、ワードクラウド画像生成は skeleton から段階実装が必要。
- 依存コストを抑えるため、初期実装は Next.js/FastAPI/CDK の full stack ではなく、静的 UI、Python Lambda handler、CloudFormation template を優先する。

## 状態

implemented_pending_pr
