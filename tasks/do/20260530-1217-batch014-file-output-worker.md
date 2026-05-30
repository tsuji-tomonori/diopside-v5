# BATCH-014 file output worker

## 背景

`.workspace/plan-20260530.txt` は基本設計 v0.4 を正本として、BATCH-001〜020 と現 worker 実装の対応を明確化し、未対応 batch を実装または差分として管理する方針を示している。
現状の BATCH-014 ファイル出力サービスは `static_export` / static exporter に寄っており、worker job としての `job_type`、queue、Artifact item 生成、単体テストの対応が弱い。

## 目的

BATCH-014 を `static_exporter.pipeline` の明示的な `file_output` job として扱えるようにし、S3/local artifact 出力と DynamoDB `Artifact` item 記録を同一経路で検証できるようにする。

## タスク種別

機能追加

## スコープ

- `file_output` job_type の handler / queue mapping / dispatch を追加する。
- file output job が public/private の出力先へ payload を書き出し、`Artifact` item を記録する。
- BATCH-014 の worker coverage / traceability / README / docs consistency を更新する。
- BATCH-014 に対する unit / contract test を追加する。

## 対象外

- 実 AWS への deploy / smoke。
- 画像 PNG 生成や wordcloud rendering の追加。
- worker package の物理分割。
- `Artifact` key schema 全体の v0.4 移行。

## 受け入れ条件

- [ ] `file_output` job_type が `static_exporter.pipeline` で dispatch できる。
- [ ] `file_output` が local/S3 書き込み helper を通じて artifact body を出力し、content hash と artifact version を含む `Artifact` item を記録する。
- [ ] `file_output` が BATCH-014 として worker coverage / traceability / README に反映される。
- [ ] BATCH-014 の unit / contract test が追加され、対象テストが pass する。
- [ ] docs consistency と whitespace check が pass する。
- [ ] PR #40 に受け入れ条件確認コメントとセルフレビューコメントを追加する。

## 実装計画

1. 既存 pipeline の dispatch / queue mapping に `file_output` を追加する。
2. `file_output` 関数で body / JSON body / content_type / visibility / bucket_env / key を検証し、`_write_blob` で書き出す。
3. `repo.put_artifact` へ `artifact_type`、`artifact_version`、`content_hash`、`public_url_path` または `s3_uri`、`generated_at` を保存する。
4. `tests/test_core_pipeline.py` と `tests/test_worker_batch_coverage_contract.py` を更新する。
5. README、worker audit、traceability、design compliance、docs consistency script を更新する。
6. 検証、レポート、commit、push、PR コメント、task done 移動まで行う。

## ドキュメント保守計画

worker job 一覧、queue 一覧、BATCH-014 coverage、traceability matrix、監査レポートの差分を更新する。v0.4 正本そのものは変更しない。

## 検証計画

- `python3 -m py_compile apps/workers/static-exporter/src/static_exporter/pipeline.py`
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_worker_batch_coverage_contract.py tests/test_repository_schema_contract.py`
- `node tools/check-docs-consistency.mjs`
- `git diff --check`
- 変更範囲と必要性に応じて `npm test` / `npm run verify`

## PRレビュー観点

- file output が本番経路で mock/fake 値を artifact として扱わないこと。
- private artifact の URI と public path を混同しないこと。
- content hash / version / generated_at が検収可能な形で保存されること。
- BATCH-014 の設計差分を実施済みとして過大に書かないこと。

## リスク

- 物理的な worker 分割は未対応のため、BATCH-014 は job_type と責務明示による部分準拠に留まる。
- 実 AWS S3 書き込みはローカルテストでは検証しない。

## 状態

in_progress
