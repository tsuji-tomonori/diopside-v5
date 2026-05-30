# BATCH-016 quota rollup

## 背景

`.workspace/plan-20260530.txt` は基本設計 v0.4 を正本として、BATCH-001〜020 を worker/job/queue/test に紐づける方針を示している。
現状の BATCH-016 `quota_rollup` は quota call record を dry summary として返すだけで、v0.4 の `QuotaUsage` daily method aggregate item を DynamoDB に保存していない。

## 目的

`quota_rollup` が既存の call record を壊さず、v0.4 形状の `QuotaUsage` daily method aggregate item を保存できるようにする。

## タスク種別

機能追加

## スコープ

- `quota_rollup` が日別・method別に `call_count` / `units_used` / `unit_per_call` を集計する。
- 集計結果を `pk=QUOTA#{yyyyMMdd}`, `sk=METHOD#{method}` の `QuotaUsage` item として upsert する。
- 既存の `GET /api/admin/quota-usage` 向け call record 一覧は aggregate item で汚染しない。
- BATCH-016 の audit / traceability / README / tests を更新する。

## 対象外

- YouTube quota reset timezone の実運用調整。
- quota threshold alarm / warning event の実装。
- 既存 call record の v0.4 key migration。

## 受け入れ条件

- [ ] `quota_rollup` が `QuotaUsage` call record から日別・method別 summary を作る。
- [ ] summary が `pk=QUOTA#{yyyyMMdd}`, `sk=METHOD#{method}` の `QuotaUsage` item として保存される。
- [ ] `list_quota_usage` は既存 API 用の call record 一覧を返し、summary item を混在させない。
- [ ] BATCH-016 の worker coverage / DDB schema audit / traceability / README が更新される。
- [ ] targeted pytest、docs consistency、whitespace check が pass する。
- [ ] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. quota call record と daily method aggregate を区別する field / key filter を追加する。
2. `quota_rollup` で call record を日別・method別に集計し、aggregate item を `repo.put_item` で upsert する。
3. Memory/Dynamo repository の `list_quota_usage` が aggregate item を除外するようにする。
4. unit / repository contract test を追加する。
5. README、DDB audit、worker batch audit、traceability、docs consistency を更新する。
6. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## ドキュメント保守計画

`README.md` の DynamoDB item schema と quota 方針、`docs/design/dynamodb-schema-audit.md`、`docs/design/worker-batch-coverage-audit.md`、`docs/design/traceability-matrix.md` を更新する。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/repository.py apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_repository_schema_contract.py tests/test_worker_batch_coverage_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- call record と aggregate item を混同して API 表示や rollup 再実行が二重計上にならないこと。
- v0.4 の key shape に寄せつつ、既存 call record 互換を壊さないこと。
- 実施していない quota threshold alarm / warning event を完了扱いしないこと。

## リスク

- quota reset timezone は現時点では call record の timestamp 日付に依存する。
- quota threshold warning event は未実装のため、BATCH-016 は daily summary 保存までの部分実装に留まる。

## 完了結果

- PR #40 本文を BATCH-016 の変更内容と検証結果で更新した。
- 受け入れ条件確認コメント: `https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581513645`
- セルフレビューコメント: `https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581513620`
- 作業レポート: `reports/working/20260530-1230-batch016-quota-rollup-report.md`

## 状態

done
