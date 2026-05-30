# FR-YT-010 重複メッセージ除外 作業レポート

## 受けた指示

- `.workspace/plan-20260530.txt` と v0.4 設計書に沿って、設計準拠差分を継続的に潰す。
- `FR-YT-010` が `要追加監査` のまま残っているため、実装・テスト証跡を確認して必要な対応を行う。

## 要件整理

- `message_id` は live/replay 正規化時に付与されている。
- `chat_normalize` は raw JSONL chunk を streaming で読み、normalized JSONL と aggregate summary を生成するため、この経路で重複除外する必要がある。
- 未実装のまま `実装済` にせず、最小実装とテストを追加する。

## 実施作業

- `apps/workers/static-exporter/src/static_exporter/pipeline.py` の `chat_normalize` に `message_id` ベースの重複除外を追加した。
- `tests/test_core_pipeline.py` の streaming normalize test に chunk をまたぐ重複 `message_id` を追加し、normalized output と summary の count が重複を含まないことを検証するよう更新した。
- `docs/design/traceability-matrix.md` の `FR-YT-010` を `実装済` に更新した。
- `reports/audit/design-v0.4-compliance-20260530.md` に FR-YT-010 の対応内容を追記した。

## 成果物

- normalized JSONL と chat aggregate summary は同一 `message_id` の重複を除外する。
- `FR-YT-010` は `要追加監査` から `実装済` に更新された。

## 検証

- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py::test_chat_normalize_streams_jsonl_chunks_without_read_jsonl_list`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `git diff --check`: pass
- `npm run verify`: pass（135 tests、build、package:deploy、local e2e）

## fit 評価

- 実装確認だけで済ませず、FR-YT-010 の期待に必要な重複除外を normalize 経路へ追加した。
- raw artifact 自体は取得結果の正本としてそのまま保持し、processed normalized/aggregate で重複を除外する方針にした。

## 未対応・制約・リスク

- `message_id` が空の raw row は今回 dedupe 対象外。通常の live/replay 正規化 row は `message_id` を持つ。
- 既存 processed artifact の backfill は未対応。
