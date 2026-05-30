# DDB common metadata

## 背景

`.workspace/plan-20260530.txt` は v0.4 DDB item schema への準拠を検収基準に戻す方針を示している。
`docs/design/dynamodb-schema-audit.md` では、現 repository の残差分として `schema_version`、`entity_id`、`created_at`、`updated_at` の共通属性が writer に不足していることを記録している。

## 目的

repository の writer 境界で DDB item 共通属性を正規化し、既存 item shape との互換を保ちながら v0.4 の共通 metadata へ寄せる。

## タスク種別

機能追加

## スコープ

- `put_item` 経路で `schema_version`、`entity_id`、`created_at`、`updated_at` を付与する。
- 既存 item の `created_at` は更新時に保持する。
- `DynamoRepository.put_item` も同じ正規化を通す。
- `DynamoRepository.create_job` の条件付き put でも正規化済み item を保存する。
- repository schema contract tests、README、DDB audit、compliance audit を更新する。

## 対象外

- v0.4 key prefix への全面移行。
- 各 item type ごとの厳密な `schema_version` 命名規約の設計変更。
- 既存 DynamoDB data の backfill。

## 受け入れ条件

- [x] `put_item` で保存される item に `schema_version`、`entity_id`、`created_at`、`updated_at` が含まれる。
- [x] `schema_version` / `entity_id` が既に指定された item では既存値を保持する。
- [x] 同じ `pk` / `sk` の更新時に既存 `created_at` を保持する。
- [x] `DynamoRepository.put_item` と `DynamoRepository.create_job` も共通 metadata 正規化を通る。
- [x] 主要 writer の contract test が共通 metadata を確認する。
- [x] README、DDB schema audit、compliance audit が更新される。
- [x] targeted tests、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [x] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. repository に item metadata 正規化 helper を追加する。
2. Memory/Dynamo の `put_item` と Dynamo の conditional job put に適用する。
3. contract tests を追加・更新する。
4. README、DDB audit、compliance audit を更新する。
5. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## ドキュメント保守計画

- README の DDB schema 説明に common metadata を追記する。
- `docs/design/dynamodb-schema-audit.md` の後続修正方針から共通属性不足を落とし、部分実装として記録する。
- `reports/audit/design-v0.4-compliance-20260530.md` の DDB schema 状態を更新する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- `created_at` が更新時に上書きされないこと。
- 既存 item の明示 `schema_version` / `entity_id` を潰さないこと。
- Memory と Dynamo の writer 経路で正規化がずれないこと。
- backfill 未実装を完了扱いしないこと。

## リスク

- 既存 DynamoDB data の backfill は未実装。
- `schema_version` は現時点では repository 互換の default 値であり、item type ごとの詳細 schema version 設計は後続対象。

## 検証結果

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`: pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`: pass（14 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（115 tests + build/package/local e2e）

## PR コメント

- 受け入れ条件確認: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581739859
- セルフレビュー: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581740190

## 状態

done
