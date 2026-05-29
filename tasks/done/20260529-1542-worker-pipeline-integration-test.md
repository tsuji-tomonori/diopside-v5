# worker pipeline integration test強化

状態: done

## 背景

`.workspace/plan-20260529.txt` の P4-03 に従い、DynamoDB/S3/SQS を mock または local fake でつないだ worker pipeline test を追加する。

## 目的

worker の主要 job を repository fake、local artifact directory、queue fake と接続して通し、job dispatch、artifact write/read、queue enqueue、job event の統合挙動を CI で検出できるようにする。

## タスク種別

integration test

## スコープ

- `tests/test_core_pipeline.py`

## 計画

1. 既存 worker pipeline と MemoryRepository/local artifact/_enqueue_job の境界を確認する。
2. `dispatch_job` 経由で metadata、live status enqueue、chat collect、normalize、artifact rebuild をつなぐ integration test を追加する。
3. local artifact directory を fake S3、MemoryRepository を fake DynamoDB、monkeypatch した `_enqueue_job` を fake SQS として検証する。
4. `npm test` / `npm run verify` で CI 対象に入ることを確認する。
5. 作業レポート、commit、PR、受け入れ条件コメント、セルフレビューまで完了する。

## ドキュメント保守方針

テスト追加であり README 更新は不要の見込み。integration test の範囲と未実施の実 AWS 確認は task md と作業レポートに残す。

## 受け入れ条件

- Worker pipeline test が fake DynamoDB 相当の repository と接続して job event / state を検証する。
- Worker pipeline test が fake S3 相当の local artifact directory と接続して raw / processed artifact の write/read を検証する。
- Worker pipeline test が fake SQS 相当の enqueue stub と接続して enqueue payload を検証する。
- 追加テストが `npm test`、ひいては CI の `npm run verify` で実行される。
- 変更範囲に見合う検証が成功する。

## 検証計画

- `git diff --check`
- targeted pytest
- `npm test`
- `npm run verify`

## 完了結果

- PR: https://github.com/tsuji-tomonori/diopside-v5/pull/35
- 受け入れ条件確認コメント: https://github.com/tsuji-tomonori/diopside-v5/pull/35#issuecomment-4570743073
- セルフレビューコメント: https://github.com/tsuji-tomonori/diopside-v5/pull/35#issuecomment-4570744227
- GitHub Actions `CI / npm verify`: 成功

## 検証結果

- `git diff --check`: 成功
- `PYTHONPATH=apps/shared/src:apps/api/src:apps/workers/static-exporter/src python3 -m pytest tests/test_core_pipeline.py -k worker_pipeline_integration`: 1 passed
- `npm run e2e:local`: 成功
- `npm test`: 62 passed
- `npm run verify`: 成功
- GitHub Actions `CI / npm verify`: 成功

## リスク

- 実 AWS DynamoDB/S3/SQS との接続確認は P4-03 の対象外。local fake による pipeline 統合確認に限定する。
