# wordcloud SVG public export 統合

状態: do
タスク種別: 機能追加

## 背景

`.workspace/plan-20260529.txt` の Phase 1 では、P1-11 として `top_terms` から deterministic な SVG を生成し、`/data/v/{export_version}/public/artifacts/wordcloud/{video_id}.svg` に出力することが求められている。既存実装には `generate_wordcloud_svg` と `rebuild_artifacts` の Artifact 登録があるが、static export の versioned public data へ SVG を出力する経路が不足している。

## 目的

chat aggregate の `top_terms` から deterministic な wordcloud SVG を生成し、static export の versioned public artifact path へ出力する。動画詳細や public contract から参照できる artifact path を保持し、CloudFront/S3 の静的公開データに統合する。

## スコープ

- 対象: static exporter、wordcloud SVG 出力、public contract/test、README、作業レポート。
- 対象 P1: P1-11。
- 対象外: UI 表示完成、timestamp 品質強化、実 S3/CloudFront deploy、画像生成サービス導入。

## 実施計画

1. static export の manifest / video detail / artifact 出力構造を確認する。
2. `top_terms` がある動画について deterministic SVG を生成し、versioned public artifact path へ出力する。
3. video detail または artifact index から wordcloud SVG path を参照できるようにする。
4. unit / contract test で SVG path、内容、determinism を確認する。
5. README に wordcloud public export 方針を追記する。

## ドキュメント保守計画

- README の S3 path / static export 説明に、wordcloud SVG の versioned public export 統合を明記する。

## 受け入れ条件

- [x] `top_terms` から deterministic な SVG が生成される。
  - 根拠: `tests/test_static_exporter.py::test_export_public_wordcloud_svg_is_deterministic`。
- [x] static export が `/data/v/{export_version}/public/artifacts/wordcloud/{video_id}.svg` 相当の versioned public path に SVG を出力する。
  - 根拠: `tests/test_static_exporter.py::test_export_public_data_from_repository`。
- [x] public video detail または artifact 情報から wordcloud SVG path を参照できる。
  - 根拠: public video detail の `chat_summary.wordcloud_url` と `artifacts.wordcloud.path`。
- [x] `top_terms` がない動画では架空の wordcloud を生成しない。
  - 根拠: `test_export_public_data_from_repository` で `vid002.svg` が存在せず、detail が `null` であることを確認。
- [x] public contract / unit test が wordcloud SVG path と content type / SVG 内容を検証する。
  - 根拠: `tools/check-public-contract.mjs` と static exporter tests。
- [x] README に wordcloud public export 方針が反映されている。
- [x] 変更範囲に応じた tests と `npm run verify` が成功する。

## 検証計画

- `git diff --check`
- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py apps/workers/static-exporter/src/static_exporter/handler.py tests/test_static_exporter.py tests/test_core_pipeline.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py tests/test_core_pipeline.py`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py apps/workers/static-exporter/src/static_exporter/handler.py tests/test_static_exporter.py tests/test_core_pipeline.py`: pass
- `node tools/check-public-contract.mjs`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py tests/test_core_pipeline.py`: pass（25 passed）
- `npm test`: 初回 fail（fixture detail に `artifacts` が未反映）-> fixture 更新後 pass（34 passed）
- `npm run verify`: pass

## PRレビュー観点

- SVG が deterministic で、test が内容を検証していること。
- `top_terms` がない動画に fake/empty wordcloud を公開しないこと。
- public path が plan の `/data/v/{export_version}/public/artifacts/wordcloud/{video_id}.svg` と整合すること。
- raw/processed/private data を public artifact に混ぜないこと。
- stacked branch である制約を PR 本文に明記すること。

## リスク

- この branch は PR #9 を土台にした stacked worktree であり、PR #3〜#9 が merge されるまで main 向け差分には前段 PR の変更も含まれる。
- 実 S3 / CloudFront での配信確認は未実施。
