# BATCH-007〜009 chat collect coverage 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と v0.4 設計書に沿って、設計準拠差分を継続的に潰す。
- BATCH-007〜009 の chat collect 周辺が `部分実装` のまま残っているため、実装・テスト証跡を確認して前進させる。

## 要件整理

- BATCH-007 公式 Live Chat 取得は、YouTube Live Chat API の page 取得、quota usage、next page requeue、停止条件、raw manifest 保存が確認できれば実装済みと扱える。
- BATCH-008/009 の replay 初期化・page collector は initial data 解析と continuation 抽出まではあるが、continuation token の実ページ取得・自己再投入 contract が不足しているため、現時点で実装済み扱いにしない。
- worker 物理分割は `WORKER-SPLIT` の差分として別管理し、BATCH-007 の機能判定と混ぜない。

## 実施作業

- `chat_collect` mode=`live` と `YouTubeClient.live_chat_messages`、対象 tests を確認した。
- `docs/design/traceability-matrix.md` の `BATCH-007` を `実装済` に更新し、implementation に `apps/shared/src/diopside_core/youtube.py` を追加した。
- `docs/design/worker-batch-coverage-audit.md` の `BATCH-007` を `実装済` に更新し、検証済みの live chat 動作を明記した。
- `reports/audit/design-v0.4-compliance-20260530.md` に BATCH-007 の実装済み根拠を追記した。

## 成果物

- BATCH-007 は `部分実装` から `実装済` に更新された。
- BATCH-008/009 は continuation page 取得 contract が不足しているため、引き続き `部分実装` として残した。

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_live_chat_collect_requeues_with_clamped_delay tests/test_core_pipeline.py::test_live_chat_collect_records_quota_when_calling_youtube tests/test_core_pipeline.py::test_live_chat_collect_stops_when_offline tests/test_core_pipeline.py::test_live_chat_collect_does_not_requeue_on_rate_limit`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（135 tests、build、package:deploy、local e2e）

## fit 評価

- 実装を過大評価せず、公式 Live Chat 取得は実装済みに更新し、replay continuation の不足は残した。
- v0.4 の完全な worker 分割は別の `WORKER-SPLIT` 差分として継続管理する。

## 未対応・制約・リスク

- BATCH-008/009 の replay continuation token からの実ページ取得と自己再投入 contract は未対応。
- 実 YouTube Live Chat API の dev 環境 rehearsal は未実施。
