# Idempotency item 対応

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、DDB item schema の差分解消が残っている。`docs/design/dynamodb-schema-audit.md` では `Idempotency` が `IDEMP#{dedupe_key}` / `META` として設計されている一方、現行実装は Memory の `idempotency_index` と DynamoDB の `Job` conditional put に依存し、独立 item が未保存と記録されている。

## 目的

`create_job` 時に v0.4 の `Idempotency` item を保存し、既存の `idempotency_key` による重複抑止と `job_id` 導出互換を維持する。

## タスク種別

機能追加

## スコープ

- `apps/shared/src/diopside_core/repository.py` の `Idempotency` item allowlist / writer / lookup。
- `tests/test_repository_schema_contract.py` の DDB schema contract。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の Idempotency 形状記述。
- 作業レポート、PR コメント、task done 更新。

## スコープ外

- 既存 DynamoDB data の backfill。
- `Job` item の `dedupe_key` rename や read model 完全移行。
- 管理 API の request field 名変更。

## 実施計画

1. 現行 `create_job` の重複抑止と `Job` conditional put を確認する。
2. `Idempotency` item helper を追加し、`ITEM_TYPES` に `Idempotency` を追加する。
3. Memory / Dynamo の `create_job` で `IDEMP#{idempotency_key}` / `META` を保存し、Memory は item lookup でも dedupe できるようにする。
4. schema contract test と audit / README を更新する。
5. targeted test、docs consistency、diff check、全体 verify を実行する。

## ドキュメントメンテナンス方針

`README.md` の item schema 表と `docs/design/dynamodb-schema-audit.md` の `Idempotency` 行を更新する。設計書本体は既に v0.4 形状を記載しているため、audit 側を実装済みに寄せる。

## 受け入れ条件

- [x] `ITEM_TYPES` が `Idempotency` を許可する。
- [x] `create_job` が新規 job 作成時に `pk=IDEMP#{idempotency_key}` / `sk=META` の `Idempotency` item を保存する。
- [x] 既存の `create_job` 重複抑止が維持され、同じ `idempotency_key` は既存 job を deduplicated として返す。
- [x] `README.md` と `docs/design/dynamodb-schema-audit.md` が実装済み形状に同期している。
- [x] 選定した検証コマンドが pass し、未実施の検証がある場合は理由を記録する。
- [x] PR に受け入れ条件確認コメントとセルフレビューコメントを日本語で追加する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- `npm run verify`

## 検証結果

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py`: pass
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`: pass（17 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（118 tests、build、package、local e2e）

## PR コメント

- 受け入れ条件確認: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581786048
- セルフレビュー: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581787229

## PR レビュー観点

- `Idempotency` item の追加が既存 `create_job` の API 互換を壊していないこと。
- DynamoDB の重複抑止は現行の `Job` conditional put を維持し、今回の独立 item 追加を過剰に同期保証したと誤記していないこと。
- backfill 未実施を PR 本文・レポートで明記していること。

## リスク

- 既存 DynamoDB job に対応する `Idempotency` item backfill は未実施。
- DynamoDB では現行どおり `Job` item の conditional put が主な重複抑止であり、`Idempotency` item 単独の conditional write へはまだ切り替えない。

## 状態

done
