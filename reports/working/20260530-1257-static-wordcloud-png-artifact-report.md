# Static wordcloud PNG artifact work report

## 受けた指示

- `.workspace/plan-20260530.txt` に沿って、v0.4 基本設計へ実装を寄せる。
- main を pull 済みの専用 worktree / PR branch で作業し、task md、検証、レポート、commit、PR 更新まで行う。

## 要件整理

- STATIC-007 は `/data/artifacts/wordcloud/{video_id}.{png|json}` を要求する。
- 既存実装は JSON alias と SVG wordcloud を出していたが、PNG が未対応だった。
- `top_terms` がない動画には fake/empty artifact を出さない。

## 検討・判断

- 外部画像ライブラリは追加せず、`top_terms` と score から deterministic な RGB PNG を生成する軽量 renderer を `diopside_core.artifacts` に追加した。
- 詳細 JSON の primary `wordcloud_url` / `artifacts.wordcloud` は PNG alias に寄せ、既存 SVG は `artifacts.wordcloud_svg` の互換 artifact として維持した。
- `STATIC-007.items` は JSON artifact のまま維持し、PNG は `STATIC-007.image_items` として manifest に追加した。

## 実施作業

- `generate_wordcloud_png` を追加し、PNG signature / IHDR / IDAT / IEND を標準ライブラリで生成するようにした。
- static exporter で versioned PNG と alias PNG を出力し、repository artifact の primary wordcloud を `image/png` に更新した。
- public fixture を再生成し、PNG artifact と manifest checksum を更新した。
- `tools/check-public-contract.mjs` で STATIC-007 PNG/JSON と detail artifact を検証するようにした。
- README、traceability、worker batch audit、v0.4 compliance audit を更新した。
- static exporter / core pipeline / worker audit tests を更新・確認した。

## 成果物

- `apps/shared/src/diopside_core/artifacts.py`
- `apps/workers/static-exporter/src/static_exporter/handler.py`
- `apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `data/fixtures/public/data/artifacts/wordcloud/fixture001.png`
- `data/fixtures/public/data/v/dev-fixture/public/artifacts/wordcloud/fixture001.png`
- `tests/test_static_exporter.py`
- `tools/check-public-contract.mjs`
- `README.md`
- `docs/design/traceability-matrix.md`
- `docs/design/worker-batch-coverage-audit.md`
- `reports/audit/design-v0.4-compliance-20260530.md`

## 検証

- `python3 -m py_compile apps/shared/src/diopside_core/artifacts.py apps/workers/static-exporter/src/static_exporter/handler.py apps/workers/static-exporter/src/static_exporter/pipeline.py`: pass
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py`: pass（7 tests）
- `node tools/check-public-contract.mjs data/fixtures/public`: pass
- `node tools/check-docs-consistency.mjs`: pass
- `PYTHONPATH=apps/shared/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_worker_batch_coverage_contract.py`: pass（46 tests）
- `git diff --check`: pass
- `npm run verify`: pass（102 tests + build/package/local e2e）

## fit 評価

- 指示適合: 4.6 / 5
- STATIC-007 の PNG/JSON artifact と contract 検証は満たした。
- v0.4 の専用 wordcloud-generator worker 分割と本格的なフォント描画は後続対象として明記した。

## 未対応・制約・リスク

- PNG renderer は標準ライブラリのみの軽量実装であり、形態素解析やフォント描画による本格 wordcloud ではない。
- 専用 `wordcloud-generator` worker、wordcloud queue、画像生成 library 採用判断は後続対象。
- 実 S3 upload / CloudFront 経路での PNG 配信は未検証。
