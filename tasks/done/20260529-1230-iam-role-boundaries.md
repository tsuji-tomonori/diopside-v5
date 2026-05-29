# IAM最小権限見直し

状態: do

## 背景

`.workspace/plan-20260529.txt` の P2-09 に従い、worker role と static-exporter role を可能なら分離する。少なくとも README に現状の権限境界と将来分離方針を書く。

## 目的

Lambda ごとの職務に合わせて IAM 権限境界を整理し、static export と worker pipeline が不要な SQS/S3 権限を持たない状態へ近づける。

## タスク種別

機能追加

## スコープ

- CloudFormation の IAM role / policy 見直し
- `StaticExporterFunction` と `WorkerFunction` の role 分離
- IAM contract test 追加
- README の権限境界説明更新

## 計画

1. 現行 role policy と各 Lambda の必要操作を確認する。
2. static exporter 専用 role と worker 専用 role に分離する。
3. policy action/resource を用途別に狭める。
4. Contract test と README を更新する。
5. 検証、作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

IAM 境界は運用・セキュリティに関わるため、README に現状の role ごとの責務、許可 action、今後の分離余地を明記する。

## 受け入れ条件

- `StaticExporterFunction` と `WorkerFunction` が別 IAM role を使う。
- static exporter role は static export に必要な DynamoDB read/write、PublicDataBucket write/read、StaticExportQueue consume に限定される。
- worker role は queue consume/send、Raw/Processed bucket read/write、DynamoDB read/write に限定され、PublicDataBucket write を持たない。
- API role は管理 job enqueue と public/admin read model に必要な権限に留まる。
- CloudFormation contract test が role 分離、action、resource 境界を検証する。
- README に現状の権限境界と将来分離方針が記載されている。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- `python3 -m pytest tests/test_cloudformation_contract.py`
- `npm test`
- 必要に応じて `npm run verify`

## PRレビュー観点

- Lambda 実行に必要な権限を落としすぎていないこと。
- queue consume と static export write の責務が分離されていること。
- 高権限 wildcard や不要な `s3:*` / `dynamodb:*` を追加していないこと。

## リスク

- 実 AWS deploy は行わないため、IAM permission の実行時検証は CloudFormation contract と既存テストに留まる。
- 今後 worker をさらに job type 別 role に分ける余地は残る。
