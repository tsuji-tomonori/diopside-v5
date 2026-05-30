# raw/processed S3 lifecycle

状態: done

## 背景

`.workspace/plan-20260529.txt` の P2-08 に従い、raw metadata、raw chat、failed debug、processed aggregate の保持期間を定義し、CloudFormation に反映する。

## 目的

個人開発向けに S3 保持期間と storage class transition を明示し、raw/processed/debug データが無期限に増え続けないようにする。

## タスク種別

機能追加

## スコープ

- RawBucket の lifecycle rule 整理
- ProcessedBucket の lifecycle rule 追加
- README の S3 path / retention 方針追記
- CloudFormation contract test 追加

## 計画

1. 現在の RawBucket / ProcessedBucket lifecycle と実際の S3 path を確認する。
2. raw metadata、raw chat、failed debug、processed aggregate の保持期間を定義する。
3. CloudFormation に lifecycle rule を追加・修正する。
4. Contract test と README を更新する。
5. 検証、作業レポート、commit、PR、受け入れ条件コメント、セルフレビューを完了する。

## ドキュメント保守方針

保持期間は運用コストと再集計可能性に関わるため、README の S3 path 設計に lifecycle 方針を明記する。

## 受け入れ条件

- raw metadata の保持期間と transition が CloudFormation に定義されている。
- raw chat の保持期間と transition が CloudFormation に定義されている。
- failed debug artifact の保持期間が CloudFormation に定義されている。
- processed aggregate / normalized chat の保持期間と transition が CloudFormation に定義されている。
- CloudFormation contract test が lifecycle rule の prefix、transition、expiration を検証する。
- README に raw/processed/debug の保持方針が記載されている。
- 変更範囲に見合う検証と `npm test` が成功する。

## 検証計画

- `git diff --check`
- `python3 -m pytest tests/test_cloudformation_contract.py`
- `npm test`
- 必要に応じて `npm run verify`

## PRレビュー観点

- 実際のアプリが書く S3 prefix と lifecycle prefix が一致していること。
- public data の immutable export を壊す lifecycle 変更をしていないこと。
- 保持期間を実施済みの実 AWS 動作として書かないこと。

## リスク

- 既存 README には raw path と CloudFormation prefix に表記差がある可能性があるため、実コードの key 生成に合わせて確認する。
- 実 S3 lifecycle の適用確認は実 AWS deploy 後の確認事項として残る。

## 完了確認

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/22
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/22#issuecomment-4570098395
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/22#issuecomment-4570100797
- 作業レポート: `reports/working/20260529-1217-s3-lifecycle-retention-report.md`
- 検証: `git diff --check`、CloudFormation targeted pytest、`npm test`、`npm run verify`
- 未実施: 実 AWS 環境での S3 lifecycle 適用確認
