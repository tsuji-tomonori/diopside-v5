# IAM最小権限見直し 作業レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づいて作業する。
- `main` から pull してから、P2-09 IAM最小権限見直しを進める。
- リポジトリの Worktree Task PR Flow に従い、task、検証、PR コメントまで行う。

## 要件整理

- `StaticExporterFunction` と `WorkerFunction` の IAM role を分離する。
- static exporter は static export に必要な DynamoDB read/write、PublicDataBucket read/write、StaticExportQueue consume に限定する。
- worker は worker queue consume/send、Raw/Processed bucket read/write、DynamoDB read/write に限定し、PublicDataBucket write を持たない。
- CloudFormation contract test で role 分離と action/resource 境界を確認する。
- README に現状の IAM 権限境界と将来の分離方針を書く。

## 検討・判断

- `StaticExporterFunction` は `StaticExportQueueMapping` から SQS event source として起動されるため、実行 role には `StaticExportQueue` の `sqs:ReceiveMessage`、`sqs:DeleteMessage`、`sqs:GetQueueAttributes` が必要。
- `WorkerFunction` は retry 経路で各 queue へ再投入するため、worker queue と `StaticExportQueue` への `sqs:SendMessage` は維持した。
- static exporter から Raw/Processed bucket への権限を外し、worker から PublicDataBucket への権限を外して、S3 の職務境界を明確にした。
- `dynamodb:Scan` は static exporter / worker の現在の実装経路に不要なため削除した。

## 実施作業

- CloudFormation に `WorkerRole` を追加し、`WorkerFunction` を `WorkerRole` に切り替えた。
- `StaticExporterRole` を PublicDataBucket と StaticExportQueue に限定し、Raw/Processed bucket と queue send 権限を外した。
- `tests/test_cloudformation_contract.py` に role 分離、wildcard 不使用、S3/SQS resource 境界の contract test を追加した。
- README に `ApiRole`、`StaticExporterRole`、`WorkerRole`、`SchedulerRole` の権限境界と将来分離方針を追記した。

## 成果物

- `infra/cloudformation/diopside.yaml`
- `tests/test_cloudformation_contract.py`
- `README.md`
- `tasks/do/20260529-1230-iam-role-boundaries.md`

## 検証

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py`: 15 passed
- `npm test`: 59 passed
- `npm run verify`: 成功
  - `npm run test`: 59 passed
  - `npm run build`: 成功
  - `npm run package:deploy`: 成功
  - `npm run e2e:local`: 成功

## fit 評価

- plan P2-09 の「worker role と static-exporter role を可能なら分離」「README に現状の権限境界と将来分離方針を書く」を満たす実装にした。
- 実装差分に対して contract test と既存 test/verify を実行し、静的な IAM policy 境界は確認した。

## 未対応・制約・リスク

- 実 AWS 環境への deploy、Lambda 実行時 IAM permission、CloudWatch alarm、S3 lifecycle の動作確認は実施していない。
- `WorkerRole` はまだ metadata/chat/normalize/aggregate を 1 role で扱う。job type ごとの Lambda/role 分離は将来対応とした。
- GitHub Apps による PR 作成・コメントが利用できない場合は、リポジトリルールに沿って理由を明記し `gh` fallback を使う。
