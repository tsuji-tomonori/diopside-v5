# Static wordcloud PNG artifact

## 背景

`.workspace/plan-20260530.txt` と v0.4 基本設計の STATIC-007 は `/data/artifacts/wordcloud/{video_id}.{png|json}` を求めている。
現状の static exporter は wordcloud JSON alias と SVG artifact を生成しているが、PNG artifact は未対応として audit に残っている。

## 目的

`ChatAggregate.top_terms` がある動画について、実データ由来の deterministic な PNG wordcloud artifact を生成し、v0.4 STATIC-007 の PNG/JSON path を public contract で検証できるようにする。

## タスク種別

機能追加

## スコープ

- `generate_wordcloud_png` を追加し、外部依存なしで deterministic な PNG bytes を生成する。
- static exporter で versioned PNG と alias PNG を出力する。
- detail JSON の `chat_summary.wordcloud_url` と `artifacts.wordcloud` を PNG artifact に寄せ、既存 SVG は互換 artifact として残す。
- public contract check、static exporter tests、README、traceability、audit を更新する。

## 対象外

- 専用 `wordcloud-generator` worker の物理分割。
- 形態素解析やフォント描画ライブラリによる本格的な単語配置。
- 既存 SVG artifact の削除。

## 受け入れ条件

- [ ] `top_terms` がある動画で `/data/artifacts/wordcloud/{video_id}.png` と versioned PNG が生成される。
- [ ] PNG は実 `top_terms` と score から deterministic に生成され、空データでは生成されない。
- [ ] detail JSON の `wordcloud_url` と `artifacts.wordcloud` が PNG artifact を指す。
- [ ] `/data/artifacts/wordcloud/{video_id}.json` は引き続き STATIC-007 JSON として生成される。
- [ ] 既存 SVG artifact は互換 artifact として残る。
- [ ] public contract check と static exporter tests が PNG/JSON 両方を検証する。
- [ ] README、traceability、audit が更新される。
- [ ] targeted tests、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [ ] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. `apps/shared/src/diopside_core/artifacts.py` に deterministic PNG generator を追加する。
2. static exporter の wordcloud artifact 書き出しを PNG primary + SVG compatibility + JSON に更新する。
3. tests と `tools/check-public-contract.mjs` を更新し、PNG signature/content-type/path を検証する。
4. README、traceability、audit を更新する。
5. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## 検証計画

- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py apps/workers/static-exporter/src/static_exporter/handler.py`
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py`
- `node tools/check-public-contract.mjs data/fixtures/public`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲に応じて `npm run verify`

## PRレビュー観点

- top_terms がない動画に fake/empty PNG を出していないこと。
- JSON alias と SVG 互換 path を壊していないこと。
- PNG artifact の content-type と path が static contract と detail JSON で一致していること。

## リスク

- 外部画像ライブラリを追加しないため、PNG は軽量 deterministic renderer に留まる。
- 専用 wordcloud worker 分割と本格的な日本語フォント描画は後続対象。

## 状態

in_progress
