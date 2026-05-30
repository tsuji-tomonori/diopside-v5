# ddb schema v0.4 audit 作業完了レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と v0.4 設計書に沿って、main を v0.4 正本へ寄せる。
- P0-08 の DynamoDB item schema 差分を未証明のまま残さない。

## 要件整理

- v0.4 の DynamoDB item type / key / GSI / required fields と、現 repository 実装の差分を repo 内で確認可能にする。
- 実装済みでない item type を実装済み扱いにしない。
- 現 repository が生成する主要 item shape は contract test で固定する。

## 検討・判断

- 現 repository は single-table、S3 退避、public/job/quota Query の大枠は v0.4 に近い。
- ただし、`VID#` ではなく `VIDEO#`、`CH#` ではなく `CHANNEL#`、`schema_version` 未付与、`ChannelRef` / `VideoMonthIndex` / `NotificationPlan` / `RandomBucket` 未対応など、既存データ互換に関わる差分がある。
- そのため本タスクでは key migration を実施せず、監査文書と contract test で現状と未対応範囲を固定した。

## 実施作業

- `docs/design/dynamodb-schema-audit.md` を追加し、v0.4 の 22 item type と現 repository/README の対応を分類した。
- `tests/test_repository_schema_contract.py` を追加し、audit coverage、現 `Video` / tag index / aggregate / artifact / quota / job の item shape、未対応 v0.4 item type の明示的 reject を検証した。
- `tools/check-docs-consistency.mjs` に DDB audit の必須 item type 検査を追加した。
- README、traceability matrix、v0.4 compliance audit を P0-08 の監査済み状態へ更新した。

## 成果物

- `docs/design/dynamodb-schema-audit.md`
- `tests/test_repository_schema_contract.py`
- `tools/check-docs-consistency.mjs`
- `README.md`
- `docs/design/traceability-matrix.md`
- `reports/audit/design-v0.4-compliance-20260530.md`

## 検証

- `node tools/check-docs-consistency.mjs`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_repository_schema_contract.py`: 成功、4 tests
- `git diff --check`: 成功
- `npm test`: 成功、82 tests
- `npm run verify`: 成功、test / build / package / local e2e

## fit 評価

- P0-08 は「未証明」から「監査済み・差分あり」へ進めた。
- v0.4 に対する未対応 item type と key/schema 差分を、後続実装や migration 判断で参照できる形にした。
- 現 repository contract をテスト化したため、移行前の互換挙動が不用意に変わるリスクを下げた。

## 未対応・制約・リスク

- v0.4 key prefix への migration、`schema_version` 共通属性付与、未対応 item type の writer/query 実装は未対応。
- 既存データ互換に関わるため、DDB schema の実修正は別タスクで migration 方針を決めてから行う。
