# DLQ運用手順 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan ファイルに基づき、main から pull してから作業する。
- P2-05 `DLQ運用手順` として、各 queue の DLQ 確認、再投入、破棄、原因調査手順を README に追加する。

## 要件整理

- CloudFormation の queue / DLQ resource 名と整合する運用手順を README に追加する。
- DLQ depth の確認、message の原因調査、安全な再投入、破棄判断、再投入後確認、再発防止観点を含める。
- 実 AWS 操作を行っていないことを明示する。

## 検討・判断

- 実 AWS deploy は行わない前提のため、手順は CloudFormation logical resource id と AWS CLI の確認例を中心にした。
- 再投入は管理 API の `retry_job` を推奨し、DLQ message の直接再投入は追跡性が崩れない緊急時に限定する方針にした。
- 破棄は不可逆操作として、事前記録と 1 件単位の削除を基本にし、bulk purge は限定条件つきにした。

## 実施作業

- `README.md` に `DLQ運用手順` 章を追加した。
- 対象 queue / DLQ と主な job の一覧を追加した。
- DLQ depth 確認、message 調査、再投入、破棄、再投入後確認、再発防止の手順を追加した。
- `tasks/do/20260529-1142-dlq-runbook.md` を作成した。

## 成果物

- `README.md`
- `tasks/do/20260529-1142-dlq-runbook.md`
- `reports/working/20260529-1142-dlq-runbook-report.md`

## 検証

- `git diff --check`: 成功
- README の DLQ resource 名が CloudFormation logical id と一致することを Python one-liner で確認: 成功
- `npm test`: 51 passed

## fit 評価

- P2-05 の DLQ 確認、再投入、破棄、原因調査手順の README 追加要件を満たした。
- 実 AWS 操作は行っていないため、実運用上の queue URL 取得や message 削除は未検証として扱う。

## 未対応・制約・リスク

- 実 AWS 環境での DLQ depth 確認、message 受信、再投入、削除は未実施。
- DLQ URL は CloudFormation Output ではなく logical resource id から取得する手順にしている。必要なら将来 PR で DLQ URL Output を追加できる。
