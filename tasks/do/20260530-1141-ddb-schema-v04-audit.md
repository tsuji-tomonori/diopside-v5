# ddb schema v0.4 audit

- 状態: do
- 種別: 設計準拠監査 / contract test
- 対象: `P0-08`, `DDB-SCHEMA`

## 背景

v0.4 設計は DynamoDB single-table の item type、key、GSI、S3 退避方針を定義している。現 main は repository と README に single-table 実装・説明があるが、v0.4 item schema との一致または差分が機械的に検証されていない。

## 受け入れ条件

- v0.4 の DynamoDB item type/key/index/schema と現 repository/README の対応を repo 内文書に整理する。
- 現 repository が生成・保存する主要 item type を contract test で検証する。
- v0.4 に対して未実装または差分が残る item type は、実装済み扱いにせず audit/traceability に明記する。
- `DDB-SCHEMA` と P0-08 の状態を、検証済みの範囲に合わせて更新する。
- `npm test` または同等の最小十分な検証で contract が通ることを確認する。

## 検証予定

- `node tools/check-docs-consistency.mjs`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_repository_schema_contract.py`
- `git diff --check`
- `npm test`
- `npm run verify`
