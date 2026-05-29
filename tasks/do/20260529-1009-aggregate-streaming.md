# aggregate streaming 化

状態: do
タスク種別: 機能追加

## 背景

`.workspace/plan-20260529.txt` の Phase 1 では、P1-10 として大量 JSONL を全件メモリに載せず、可能な範囲で stream / line iteration で集計することが求められている。現在の `chat_normalize` は `chunks` ごとに `_read_jsonl` で list 化し、さらに全 message を list にまとめてから集計しているため、大量チャットでメモリ使用量が増える。

## 目的

raw chat JSONL を line iteration で読み、集計 summary を streaming accumulator で作成する。normalized JSONL 出力は従来どおり維持しつつ、集計用には全 message list を作らない経路へ移行する。

## スコープ

- 対象: chat aggregate helper、`chat_normalize`、JSONL reader、unit test、README、作業レポート。
- 対象 P1: P1-10。
- 対象外: wordcloud SVG public export、timestamp 品質強化、実 S3 streaming body 最適化、UI 表示変更。

## 実施計画

1. 既存 `summarize_chat_messages` と `chat_normalize` の message list 化箇所を確認する。
2. iterable 入力を受け取る streaming accumulator を追加し、既存 summary output contract を維持する。
3. `_iter_jsonl` を追加し、local/S3/object key の JSONL を 1 行ずつ yield する。
4. `chat_normalize` は normalized JSONL へ書き出しながら streaming 集計する。
5. list materialization を検知できる targeted test を追加する。
6. README に streaming aggregate 方針を追記する。

## ドキュメント保守計画

- README に `chat_normalize` が raw JSONL を line iteration で処理し、集計用に全件 list 化しないことを追記する。

## 受け入れ条件

- [x] `summarize_chat_messages` が list 以外の iterable でも既存 summary contract を返す。
  - 根拠: `tests/test_core_pipeline.py::test_summarize_chat_messages_accepts_single_pass_iterable`。
- [x] `chat_normalize` が raw JSONL を全件 list 化せず、line iteration で normalized JSONL と aggregate summary を出力する。
  - 根拠: `tests/test_core_pipeline.py::test_chat_normalize_streams_jsonl_chunks_without_read_jsonl_list`。
- [x] normalized JSONL と aggregate summary の出力 path / JSON contract が既存互換である。
  - 根拠: `tests/test_core_pipeline.py::test_pipeline_collect_normalize_and_artifacts` と streaming test。
- [x] local artifact mode の JSONL chunk を複数 chunk から streaming 集計できる。
  - 根拠: streaming test で 2 chunk から summary / normalized rows を確認。
- [x] README に aggregate streaming 方針が反映されている。
- [x] 変更範囲に応じた tests と `npm run verify` が成功する。

## 検証計画

- `git diff --check`
- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py apps/workers/static-exporter/src/static_exporter/pipeline.py tests/test_core_pipeline.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py apps/workers/static-exporter/src/static_exporter/pipeline.py tests/test_core_pipeline.py`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py`: pass（21 passed）
- `npm test`: pass（33 passed）
- `npm run verify`: pass

## PRレビュー観点

- summary output が既存 public/processed contract を壊していないこと。
- chat_normalize が集計用に全 message list を作らないこと。
- normalized JSONL 出力のために必要な最小限の逐次書き出しになっていること。
- 実 S3 / AWS 疎通を実施していない制約を PR に明記すること。
- stacked branch である制約を PR 本文に明記すること。

## リスク

- この branch は PR #8 を土台にした stacked worktree であり、PR #3〜#8 が merge されるまで main 向け差分には前段 PR の変更も含まれる。
- 実 S3 streaming body と大規模実データでのメモリ測定は未実施。
