# raw/processed S3 lifecycle 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan ファイルに基づき、main から pull してから作業する。
- P2-08 `raw/processed S3 lifecycle` として、raw metadata、raw chat、failed debug、processed aggregate の保持期間を定義し、CloudFormation に反映する。

## 要件整理

- 実コードが書き込む S3 prefix に合わせて lifecycle rule を定義する。
- RawBucket に raw metadata、raw chat、failed debug の保持期間を設定する。
- ProcessedBucket に normalized chat、processed aggregate の保持期間を設定する。
- Public data の immutable export 契約を壊さない。
- README と contract test を更新する。

## 検討・判断

- 既存 CloudFormation の `RawBucket` lifecycle は `youtube/raw/metadata/` prefix だったが、実コードは `raw/youtube/metadata/...` へ書き込むため、実 path に合わせて修正した。
- raw chat は再取得や再集計に使うが容量が増えやすいため、30 日で `STANDARD_IA`、180 日で expire とした。
- raw metadata は比較的小さく追跡価値があるため、90 日で `STANDARD_IA`、365 日で expire とした。
- processed normalized / aggregate は再利用価値が高いため、90 日で `STANDARD_IA`、730 日で expire とした。
- public data の versioned export は manifest 差し替え契約に関わるため、今回の Raw/Processed lifecycle とは分けて扱った。

## 実施作業

- `infra/cloudformation/diopside.yaml` の `RawBucket` lifecycle prefix を実コードの S3 key に合わせて修正した。
- `RawBucket` に raw chat lifecycle rule を追加した。
- `ProcessedBucket` に normalized chat と chat aggregate lifecycle rule を追加した。
- `tests/test_cloudformation_contract.py` に lifecycle contract test を追加した。
- `README.md` に raw/processed/debug の保持方針を追記した。
- `tasks/do/20260529-1217-s3-lifecycle-retention.md` を作成した。

## 成果物

- `infra/cloudformation/diopside.yaml`
- `tests/test_cloudformation_contract.py`
- `README.md`
- `tasks/do/20260529-1217-s3-lifecycle-retention.md`

## 検証

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_cloudformation_contract.py`: 14 passed
- `npm test`: 58 passed
- `npm run verify`: 成功

## fit 評価

- P2-08 が求める raw metadata、raw chat、failed debug、processed aggregate の保持期間定義と CloudFormation 反映を満たした。
- processed normalized chat も同じ ProcessedBucket の主要成果物として lifecycle を追加した。

## 未対応・制約・リスク

- 実 AWS 環境での S3 lifecycle 適用確認は未実施。
- public data の lifecycle は今回対象外とし、immutable export と manifest 差し替え契約を維持した。
