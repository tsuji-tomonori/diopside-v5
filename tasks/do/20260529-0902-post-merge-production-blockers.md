# PR #2 merge後の本番ブロッカー解消

状態: do
タスク種別: 修正

## 背景

`.workspace/plan-20260529.txt` は、PR #2 merge後に本番投入前の安全化PRとして P0-01 から P0-08 を優先する方針を示している。根拠設計は `.workspace/diopside_basic_design_v0.4.md` であり、低コスト serverless 構成、DynamoDB single-table、S3 JSONL 正本、JobEvent append-only、fixture 非依存の本番経路を前提にする。

## 目的

main 取り込み後の実装を、本番デプロイ後に即時に踏む可能性が高い不整合が残らない状態へ近づける。特に `/api/home` の本番 repository 経路、チャット本文の DynamoDB 保存廃止、S3 JSONL からの chat normalize、YouTube API key 注入、replay chat offset、retry/cancel の露出整合、post-deploy smoke、既知リスク記録を扱う。

## スコープ

- 対象: API、shared repository/chat/youtube、static-exporter worker、CloudFormation、README、tests、smoke script、作業レポート。
- 対象外: 実 AWS deploy、実 YouTube API 呼び出し、P1 以降の大規模 pipeline 完成。

## なぜなぜ分析サマリ

### 問題文

PR #2 merge直後の main には、設計上は本番データ経路を目指している一方で、`.workspace/plan-20260529.txt` が列挙する P0 ブロッカーが残り、本番 deploy 後に `/api/home`、chat normalize、worker secret 注入、job 再実行/取消、post-deploy smoke のいずれかで期待仕様から外れる可能性がある。

### 確認済み事実

- `main` は PR #2 merge commit `8b4272a` まで fast-forward 済み。
- `README.md` は DynamoDB/S3/YouTube を本番経路とする説明を含む。
- `.workspace/plan-20260529.txt` は P0-01 から P0-08 を「本番投入前に必須の修正」として列挙している。
- `.workspace/diopside_basic_design_v0.4.md` はチャット全文を S3 に置き、DynamoDB には manifest/summary のみを置く設計を示している。

### 推定原因

- skeleton から production path へ段階移行したため、public API、repository、worker、infra、smoke の境界で fixture/local 前提と本番前提が混在している。
- 大型チャットデータの保管責務が DynamoDB item と S3 JSONL の間で完全には分離されていない可能性がある。
- README と API が retry/cancel を示している一方、worker 側の実処理または明示拒否が追いついていない可能性がある。

### 根本原因

本番経路化の変更が複数レイヤーにまたがるにもかかわらず、P0 の本番ブロッカーを一括で検出する contract/unit/smoke が十分に固定されていないこと。対策として、実装と同時に P0 条件をテスト・smoke・README・作業レポートへ落とし込む。

### 対策方針

- P0 各項目を code path と test で検証できる形にする。
- fixture は local test 用に限定し、本番環境変数がある経路で fixture fallback しない。
- retry/cancel は worker 実装または明示的拒否を API/UI/README と整合させる。
- post-deploy smoke は `/api/home`、static-export job、manifest、versioned public JSON を確認対象に含める。

## 実施計画

1. 既存 API/repository/worker/infra/test を読み、P0 項目ごとの差分を特定する。
2. P0-01 から P0-07 を実装し、必要な README 更新を行う。
3. P0-08 として `reports/working/` に既知未完了と解消予定を記録する。
4. 変更範囲に応じた unit/contract/smoke/build を実行する。
5. 作業完了レポートを作成し、commit、push、main 向け PR、受け入れ条件コメント、セルフレビューコメントまで行う。

## ドキュメント保守計画

- CloudFormation 環境変数、YouTube API key、retry/cancel、post-deploy smoke の挙動が変わる場合は README を更新する。
- 設計そのものの新規要求追加ではなく P0 修正のため、`docs/` 追加は必要性を確認して最小限にする。

## 受け入れ条件

- [x] P0-01: `DIOPSIDE_TABLE_NAME` が設定された repository mode で `GET /api/home` が 200 を返し、`latest-manifest.json` 読み込みに依存しない。
  - 根拠: `apps/api/src/diopside_api/handler.py`、`tests/test_api_handler.py::test_home_uses_repository_when_table_name_is_configured`。
- [x] P0-02: `ChatMessageChunkManifest` 相当の永続 item からチャット本文 `messages` 配列を保存しない。
  - 根拠: `apps/workers/static-exporter/src/static_exporter/pipeline.py`、`tests/test_core_pipeline.py::test_pipeline_collect_normalize_and_artifacts`。
- [x] P0-03: `chat_normalize` は DynamoDB item 内の `messages` ではなく S3 JSONL chunk を読んで集計し、local artifact mode でも同じ処理経路を通る。
  - 根拠: `apps/workers/static-exporter/src/static_exporter/pipeline.py`、`tests/test_core_pipeline.py::test_chat_normalize_reads_s3_jsonl_manifest_not_dynamodb_messages`。
- [x] P0-04: CloudFormation から `WorkerFunction` へ `DIOPSIDE_YOUTUBE_API_KEY` を注入する経路があり、README の deploy 手順にも反映されている。
  - 根拠: `infra/cloudformation/diopside.yaml`、`README.md`、`tests/test_cloudformation_contract.py::test_cloudformation_template_parses_and_worker_can_consume_queues`。
- [x] P0-05: replay chat offset は `replayChatItemAction.videoOffsetTimeMsec` から取得し、renderer 内 offset へ依存しない golden fixture test がある。
  - 根拠: `apps/shared/src/diopside_core/chat.py`、`tests/test_core_pipeline.py::test_replay_parser_normalizes_known_and_unknown_renderer`。
- [x] P0-06: `retry_job` / `cancel_job` は worker で実装されるか、API/UI/README から削除または明示拒否として整合している。
  - 根拠: `apps/workers/static-exporter/src/static_exporter/pipeline.py`、`README.md`、`tests/test_core_pipeline.py::test_retry_and_cancel_job_update_target_events`。
- [x] P0-07: post-deploy smoke は `GET /api/home`、`static-export` job 完了、`latest-manifest.json` 更新、versioned public JSON 取得を対象に含む。
  - 根拠: `tools/run-post-deploy-smoke.mjs`、`node --check tools/run-post-deploy-smoke.mjs`。
- [x] P0-08: `reports/working/` に「マージ時点の既知未完了」と「後続PRでの解消予定」を記録する。
  - 根拠: `reports/working/20260529-0902-post-merge-known-gaps.md`。
- [x] `npm run verify` が成功する。
- [x] `node --check tools/run-post-deploy-smoke.mjs` が成功する。

## 検証計画

- `git diff --check`
- `node --check tools/run-post-deploy-smoke.mjs`
- `npm test`
- `npm run verify`

## 検証結果

- `git diff --check`: pass
- `node --check tools/run-post-deploy-smoke.mjs`: pass
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py tests/test_api_handler.py tests/test_static_exporter.py tests/test_cloudformation_contract.py`: pass
- `npm test`: pass
- `npm run verify`: pass

## PRレビュー観点

- docs と実装の同期。
- fixture fallback が本番経路に残っていないこと。
- DynamoDB item にチャット本文を保存しないこと。
- RDB/OpenSearch/ECS/EC2/常時起動サーバーを追加していないこと。
- 未実施検証を実施済みとして扱っていないこと。

## リスク

- 実 AWS deploy と実 YouTube API 呼び出しは行わないため、AWS 権限・実 quota・実データ量に起因する問題は post-deploy smoke の対象として残る。
- P1 以降の pipeline 完成タスクは本タスクでは完了扱いにしない。
