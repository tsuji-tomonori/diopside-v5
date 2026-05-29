# S3 bucket policy / OAC検証 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づき、main を pull してから継続作業する。
- P2-03「S3 bucket policy / OAC検証」として、WebBucket / PublicDataBucket が CloudFront OAC 以外から読めないことを template contract test で検証する。

## 要件整理

- Web/PublicData S3 bucket は public access block を有効にする。
- CloudFront origin は S3 website endpoint ではなく REST origin + OAC を使う。
- bucket policy は CloudFront service principal、対象 distribution ARN、`s3:GetObject` のみに限定する。
- public principal や broad read allow を contract test で検出する。

## 検討・判断

- 既存 template は bucket policy を持っていたが、文字列 token 確認だけでは条件の抜けを検出できないため、YAML 構造を直接検証する test を追加した。
- `AWS:SourceArn` は `arn:aws:` 固定から `arn:${AWS::Partition}:` に変更し、partition 非依存にした。
- bucket policy は CloudFront OAC 以外からの read allow を追加しない方針を contract test で固定した。

## 実施作業

- `WebBucketPolicy` と `PublicDataBucketPolicy` の `AWS:SourceArn` を `AWS::Partition` 対応に修正。
- `tests/test_cloudformation_contract.py` に S3 OAC 設定、REST origin、bucket policy 条件、public access block の構造検証を追加。
- README に Web/PublicData bucket が CloudFront OAC 経由の `s3:GetObject` のみ許可することを追記。

## 成果物

- S3 OAC / bucket policy contract test の強化。
- 作業 task: `tasks/do/20260529-1123-s3-oac-bucket-policy-contract.md`

## 検証

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py`: 9 passed
- `npm test`: 46 passed
- `npm run verify`: 成功

## fit 評価

- P2-03 の WebBucket / PublicDataBucket が CloudFront OAC 以外から読めない条件は、public access block、REST origin + OAC、bucket policy principal/action/resource/source arn の contract test で検証される。

## 未対応・制約・リスク

- 実 CloudFront / AWS 環境への deploy と S3 直接アクセス拒否の実地確認は、対象環境が必要なため未実行。
- `s3:GetObject` 以外の write 権限は Lambda role policy 側で別途管理しており、今回の bucket policy contract の対象外。
