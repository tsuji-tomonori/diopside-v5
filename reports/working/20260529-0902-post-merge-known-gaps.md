# PR #2 merge時点の既知未完了と後続解消予定

## 受けた指示

- `.workspace/` 配下の設計書と 2026-05-29 の plan をもとに作業する。
- main から pull してから作業する。
- PR #2 merge後の完全実装化に向け、P0 の本番ブロッカーを優先する。

## 既知未完了

| ID | 既知未完了 | 影響 | 本PRでの扱い |
|---|---|---|---|
| P0-01 | `/api/home` が DynamoDB repository mode でも `latest-manifest.json` を参照する | 本番 table 設定時に fixture/public data manifest へ依存する | 修正対象 |
| P0-02 | `ChatMessageChunkManifest` にチャット本文 `messages` が保存される | DynamoDB item size がチャット件数に比例して増える | 修正対象 |
| P0-03 | `chat_normalize` が DynamoDB item 内の `messages` を読む | S3 JSONL 正本という設計から外れる | 修正対象 |
| P0-04 | WorkerFunction への YouTube API key 注入経路がない | metadata/live chat worker が本番で YouTube API を呼べない | 修正対象 |
| P0-05 | replay chat offset の取得位置が renderer 内に寄っている | 実 replay 構造で offset が欠落・誤読される | 修正対象 |
| P0-06 | `retry_job` / `cancel_job` が API 上は存在するが worker 未対応 | 運用APIを実行しても worker が失敗する | 修正対象 |
| P0-07 | post-deploy smoke が `/api/home` や static-export job 完了、manifest 更新を十分に確認しない | deploy 後に公開データ更新失敗を見逃す | 修正対象 |

## 後続PRでの解消予定

- P1 以降で、DynamoDB repository の GSI Query 化、metadata pagination、raw response 保存の網羅、live/replay chat collector の実データ検証、public data contract 強化を進める。
- P2 以降で、CloudFront/OAC の実 deploy 後検証、EventBridge Scheduler、DLQ runbook、CloudWatch alarm、S3 lifecycle の運用強化を進める。
- P3 以降で、検索ハブ、filter bottom sheet、動画詳細、履歴/お気に入り、管理job UI を完成させる。
- P4 以降で、GitHub Actions CI、package artifact 検証、integration test、replay parser golden fixtures、YouTube client error test、cost guard、docs consistency を強化する。

## 制約

- 実 AWS deploy と実 YouTube API 呼び出しは行わない。
- P1 以降の完全 pipeline 完成は本PRの完了条件に含めない。
