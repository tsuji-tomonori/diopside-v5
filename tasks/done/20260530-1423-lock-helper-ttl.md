# Lock helper / TTL 対応

## 背景

`.workspace/plan-20260530.txt` の v0.4 設計準拠対応では、DDB item schema の差分解消が残っている。`docs/design/dynamodb-schema-audit.md` では `Lock` が `LOCK#{lock_key}` / `META` として許可済みだが、取得/解放 helper と TTL contract が未実装と記録されている。

## 目的

Repository に v0.4 の短期排他 lock 取得/解放 helper を追加し、`lock_key`、`owner_job_id`、`owner_request_id`、`acquired_at`、`expires_at` を持つ `Lock` item を保存できるようにする。

## タスク種別

機能追加

## スコープ

- `apps/shared/src/diopside_core/repository.py` の `Lock` item helper、Memory/Dynamo repository method。
- `tests/test_repository_schema_contract.py` の DDB schema contract。
- `README.md` と `docs/design/dynamodb-schema-audit.md` の Lock 形状記述。
- 作業レポート、PR コメント、task done 更新。

## スコープ外

- worker pipeline への lock 適用。
- 既存 DynamoDB data の backfill。
- lock contention の全運用設計や CloudWatch alarm。

## 実施計画

1. v0.4 の `Lock` item schema と現 repository の allowlist を確認する。
2. `acquire_lock` / `release_lock` を Repository protocol と Memory/Dynamo implementation に追加する。
3. Memory は未期限切れ lock を拒否し、期限切れ lock は上書きできるようにする。
4. Dynamo は `attribute_not_exists(pk) OR expires_at < now OR owner_job_id = :owner_job_id` の conditional put で取得し、owner 一致時のみ release する。
5. schema contract test と audit / README を更新する。
6. targeted test、docs consistency、diff check、全体 verify を実行する。

## ドキュメントメンテナンス方針

`README.md` の item schema 表と `docs/design/dynamodb-schema-audit.md` の `Lock` 行を更新する。設計書本体は既に v0.4 形状を記載しているため、audit 側を実装済みに寄せる。

## 受け入れ条件

- [x] `acquire_lock` が `pk=LOCK#{lock_key}` / `sk=META` の `Lock` item を保存する。
- [x] `Lock` item が `lock_key`、`owner_job_id`、`owner_request_id`、`acquired_at`、`expires_at` を持つ。
- [x] 未期限切れ lock は別 owner から取得できず、同 owner または期限切れ lock は取得できる。
- [x] `release_lock` が owner 一致時だけ lock を削除する。
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
- `PYTHONPATH=apps/shared/src python3 -m pytest tests/test_repository_schema_contract.py`: pass（19 tests）
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（120 tests、build、package、local e2e）

## PR コメント

- 受け入れ条件確認: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581806539
- セルフレビュー: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581807494

## PR レビュー観点

- TTL は UNIX epoch seconds として保存されること。
- DynamoDB conditional put が既存 lock の上書きを不用意に許可しないこと。
- worker への実適用や backfill を実施済みと誤記していないこと。

## リスク

- 今回は repository helper の contract 固定であり、worker job への lock 適用は後続。
- DynamoDB の release は owner 一致条件で削除するが、local unit は MemoryRepository 中心のため実 AWS 条件式は未実行。

## 状態

done
