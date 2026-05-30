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

- [x] `top_terms` がある動画で `/data/artifacts/wordcloud/{video_id}.png` と versioned PNG が生成される。
- [x] PNG は実 `top_terms` と score から deterministic に生成され、空データでは生成されない。
- [x] detail JSON の `wordcloud_url` と `artifacts.wordcloud` が PNG artifact を指す。
- [x] `/data/artifacts/wordcloud/{video_id}.json` は引き続き STATIC-007 JSON として生成される。
- [x] 既存 SVG artifact は互換 artifact として残る。
- [x] public contract check と static exporter tests が PNG/JSON 両方を検証する。
- [x] README、traceability、audit が更新される。
- [x] targeted tests、docs consistency、whitespace check、必要に応じて `npm run verify` が pass する。
- [x] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

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

## 完了結果

- 実装 commit: `4415192` (`✨ feat(static): wordcloud PNG artifactを追加`)
- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/40
- PR 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581586558
- PR セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/40#issuecomment-4581586556
- 作業レポート: `reports/working/20260530-1257-static-wordcloud-png-artifact-report.md`

### 検証結果

- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py apps/workers/static-exporter/src/static_exporter/handler.py apps/workers/static-exporter/src/static_exporter/pipeline.py`: pass
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py`: pass（7 tests）
- `node tools/check-public-contract.mjs data/fixtures/public`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_worker_batch_coverage_contract.py`: pass（46 tests）
- `git diff --check`: pass
- `npm run verify`: pass（102 tests + build/package/local e2e）

### 後続対象

- 専用 `wordcloud-generator` worker と wordcloud queue。
- 画像生成ライブラリやフォント描画を使う本格的な wordcloud renderer。
- 実 S3 upload / CloudFront 経路での PNG 配信確認。

## 状態

done
