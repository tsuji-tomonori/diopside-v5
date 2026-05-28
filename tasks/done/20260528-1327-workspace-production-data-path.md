# .workspace plan 本番データ経路実装

## 背景

ユーザーから「main pullしてから」「.workspace にある基本設計をもとに .workspace/plan.md の作業を行って」と依頼された。

`main` は 2026-05-28 に `origin/main` から fast-forward pull 済みで、PR #1 相当の deployable skeleton が取り込まれている。一方、`.workspace/plan.md` は skeleton で止めず、DynamoDB/S3/YouTube を正本とした本番データ経路、worker、CloudFront、公開 UI、管理 job、検証、README までを要求している。

## 目的

`.workspace/diopside_basic_design_v0.4.md` と `.workspace/plan.md` に沿って、低コスト serverless 構成のまま、fixture copy skeleton ではなく本番データ経路でデプロイ後 E2E 検証へ進める状態にする。

## スコープ

- CloudFront/OAC/path/cache behavior と Outputs の CloudFormation 更新。
- DynamoDB single-table repository と item schema/access pattern の実装・文書化。
- YouTube metadata sync、live status scan、live/replay chat collect、chat normalize/aggregate、wordcloud SVG、timestamp、static export の worker 実装。
- 公開 API と管理 API の本データ対応、ErrorResponse 統一、JSON body validation、job 冪等性。
- モバイルファースト UI、filter bottom sheet、履歴/お気に入り、管理 job 画面。
- テスト、deploy artifact、README、作業レポート。

## タスク種別

機能追加

## 実装前チェックリスト

- [x] `.workspace/plan.md` と基本設計の要求を、既存実装差分に照らして未実装リスト化する。
- [x] 本番経路に fixture copy、dummy response、空配列固定、skeleton 言い逃れが残らないようにする。
- [x] 実 AWS deploy は行わず、artifact/template/README/post-deploy e2e コマンドを完成させる。
- [x] SQL 系 DB、OpenSearch、ECS、EC2、常時起動サーバーを追加しない。
- [x] API/管理操作の認証境界、CSRF、返却 schema を確認する。
- [x] UI では本番経路に架空値や demo fallback を混入させない。

## Done 条件

- [x] CloudFormation に CloudFront Distribution、OAC、S3 bucket policy、path/cache behavior、SPA fallback、必要 Outputs が含まれる。
- [x] DynamoDB repository が AppConfig、Channel、ChannelCursor、Video、VideoIndex、VideoTagIndex、ChatManifest、ChatMessageChunkManifest、ChatAggregate、Artifact、Job、JobEvent、QuotaUsage、Lock を扱える。
- [x] job が idempotency_key により二重起動を避け、JobEvent は append-only として状態を導出できる。
- [x] YouTube metadata sync は uploads playlist と videos.list を使い、quota usage と raw response 保存と正規化 Video 保存を行える。
- [x] live status scan と live chat collect は長時間 sleep せず、nextPageToken/pollingIntervalMillis/rateLimitExceeded を job event と再投入情報で扱える。
- [x] replay chat parser は主要 renderer と未知 renderer を安全に正規化し、golden fixture test がある。
- [x] chat normalize/aggregate は processed JSONL、summary、top_terms、timeline buckets、DynamoDB manifest/artifact を生成する。
- [x] wordcloud SVG と timestamp candidate を生成し、動画詳細 public JSON に反映する。
- [x] static exporter は DynamoDB/S3 read model から public JSON/artifacts を生成し、fixture copy だけの本番経路ではない。
- [x] 公開 API と管理 API が DynamoDB/S3 read model と job repository を使い、ErrorResponse と body validation が統一される。
- [x] Web UI が検索ハブ、片手フィード、詳細、filter bottom sheet、履歴/お気に入り、管理 job 操作を実データ/明示 empty state で扱う。
- [x] README に全体構成、CloudFront path、DynamoDB schema、S3 path、環境変数、YouTube API key、deploy、post-deploy e2e、quota、job 一覧を記載する。
- [x] `npm run verify` が成功する。
- [x] `git diff --check` が成功する。
- [x] 作業レポートを `reports/working/` に追加する。
- [x] PR 作成後、受け入れ条件確認とセルフレビューを日本語コメントで記載する。

## PR

- https://github.com/tsuji-tomonori/diopside-v5/pull/2

## 追加監査・補強

- 2026-05-28 15:04: DynamoDB 実行時の repository surface と fixture fallback 明示性を再監査し、追加修正した。
- 追加作業レポート: `reports/working/20260528-1504-production-path-audit-repair.md`
- 追加検証: `npm test` pass、`npm run verify` pass、`git diff --check` pass。
- 2026-05-28 15:09: live/replay worker、failed debug artifact、管理 UI、admin dry-run e2e を追加補強した。
- 追加作業レポート: `reports/working/20260528-1509-worker-admin-e2e-hardening.md`
- 追加検証: `npm test` pass、`npm run e2e:local` pass、`npm run verify` pass、`git diff --check` pass。
- 2026-05-28 15:13: worker Lambda の SQS consume 権限と queue URL env を補強し、CloudFormation parse test を追加した。
- 追加作業レポート: `reports/working/20260528-1513-cloudformation-worker-permissions.md`
- 追加検証: `npm test` pass、`npm run verify` pass、`git diff --check` pass。

## 検証計画

- `npm test`
- `npm run build`
- `npm run package:deploy`
- `npm run e2e:local`
- `npm run verify`
- `git diff --check`

## PR レビュー観点

- docs と実装の同期。
- 変更範囲に見合うテスト。
- RAG は含まないが、公開 API と管理 API の認可境界を弱めていないこと。
- benchmark 期待語句、QA sample 固有値、dataset 固有分岐を実装へ入れていないこと。
- fixture はテスト/local fixture として分離され、本番処理の暗黙 fallback になっていないこと。

## リスク

- 実 YouTube API と実 AWS deploy は実施しないため、資格情報や外部サービス固有の runtime 挙動は post-deploy e2e で最終確認が必要。
- 依存最小方針のため、公式 SDK がない環境では HTTP/urllib ベース実装と botocore optional import fallback で検証する。
- 全要求の実装範囲が広いため、途中で未検証や未達が残った場合は完了扱いにせず、部分完了/blocked として記録する。

## 状態

done
