# public data contract強化 作業完了レポート

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan に基づき、main を pull してから継続作業する。
- P1-14「public data contract強化」として、manifest、video list、tags、video detail、wordcloud、timestamp、artifact path の契約検証を fixture / exporter output / post-deploy 取得物に対して実行できるようにする。

## 要件整理

- local fixture と static exporter output の両方で同一の `tools/check-public-contract.mjs` を通す。
- post-deploy smoke が取得した public data にも同一 checker を適用する。
- 実施していない実環境確認は実施済み扱いにしない。

## 検討・判断

- 契約検証は schema 名だけでなく、manifest `base_path` と `export_version`、versioned path、video list と detail の相互整合、tag/search index、wordcloud SVG 実体、timestamp candidate field まで確認する形にした。
- checker 強化で fixture export の `export_version` と path がずれる既存挙動が検出されるため、fixture export 時も `/data/v/{export_version}/public/...` に揃えるよう補正した。
- post-deploy smoke では wordcloud URL を読むだけでは checker が artifact 実体を確認できないため、取得した SVG を一時 directory に保存するよう変更した。

## 実施作業

- `tools/check-public-contract.mjs` を拡張し、manifest/index/search/detail/tag/wordcloud/timestamp の整合性を検証。
- `tools/run-post-deploy-smoke.mjs` で wordcloud SVG 取得物を保存し、同一 checker で検証可能にした。
- `export_from_fixture` が export version に合わせて manifest、index path、detail 内 path、配置 directory を更新するよう修正。
- fixture の timestamp candidate を `score`、`evidence_terms`、`message_count` を含む現行 schema に更新。
- `tests/test_static_exporter.py` で fixture export output に対しても contract check を実行。
- README に contract check の対象と post-deploy 観点を追記。

## 成果物

- public data contract checker の強化。
- fixture export output の versioned path 整合修正。
- post-deploy 取得物に wordcloud artifact 実体を含める smoke 更新。
- 作業 task: `tasks/done/20260529-1046-public-contract-hardening.md`

## 検証

- `git diff --check`: 成功
- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/handler.py`: 成功
- `node --check tools/check-public-contract.mjs`: 成功
- `node --check tools/run-post-deploy-smoke.mjs`: 成功
- `node tools/check-public-contract.mjs`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_static_exporter.py`: 6 passed
- `npm test`: 37 passed
- `npm run verify`: 成功

## fit 評価

- P1-14 の対象である manifest、video list、tags、video detail、wordcloud、timestamp、artifact path の検証は checker に含めた。
- fixture と exporter output は automated test で実行される。
- post-deploy 取得物は smoke 実行時に一時 directory へ保存され、同一 checker で検証される。

## 未対応・制約・リスク

- 実 CloudFront / AWS 環境に対する `npm run smoke:post-deploy` は、対象 URL と認証情報が必要なため未実行。
- manifest の checksum 検証は現行 exporter が checksum を生成していないため未対応。将来 checksum を出力する時点で contract に追加する。
