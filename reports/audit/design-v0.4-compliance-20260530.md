# design v0.4 compliance audit

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-05-30 |
| 対象設計 | `docs/design/diopside_basic_design_v0.4.md` |
| 照合対象 | `origin/main` 由来の現 worktree |
| 方針 | v0.4 を正本とし、実装差分は未対応または差分ありとして扱う。 |

## 1. 要約

`.workspace/plan-20260530.txt` の最初の PR 方針に沿って、v0.4 設計書を repository 内に正本化し、現在の `main` 実装との初版 traceability を作成した。

現 main は CloudFront + S3 + Lambda + DynamoDB + SQS + EventBridge という低コスト serverless の大枠に近い。一方で、v0.4 が正本とする AWS CDK、FastAPI on Lambda、Next.js static export、外部通知 delivery などには差分または未対応が残る。STATIC-001〜008 は同 PR 内の追加 commit で alias path と manifest checksum の contract 対応を進め、wordcloud は PNG/JSON alias と互換 SVG を出力する。API-007/API-022/API-023 は既存 Lambda handler に追加し、API-008/API-009/API-013/API-015/API-016/API-019 は route contract test を追加した。FastAPI adapter と OpenAPI 3.1 contract は追加したが、FastAPI/Mangum 依存同梱と Lambda entrypoint 切替は後続課題として残す。ADMIN-SESSION は HttpOnly cookie + CSRF を追加し、CLI / automation 向け Bearer fallback は維持した。DDB schema は v0.4 item type との差分を audit 化し、現 repository contract をテストで固定した。Worker coverage は BATCH-001〜020 の対応を audit 化し、現 pipeline の job_type / queue mapping を contract test で固定した。BATCH-006 は `notification_plan` job と `NotificationPlan` item 作成まで、BATCH-017 は `archive_finalize` job として replay collect / static export 投入まで部分実装した。

## 2. 正本化

| 項目 | 結果 |
|---|---|
| v0.4 設計書 | `docs/design/diopside_basic_design_v0.4.md` に配置 |
| README 設計根拠 | `.workspace/diopside_basic_design_v0.4.md` から `docs/design/diopside_basic_design_v0.4.md` へ変更 |
| traceability | `docs/design/traceability-matrix.md` に作成 |

## 3. P0 準拠ブロッカー

| ID | 項目 | 現状 | 判定 | 次アクション |
|---|---|---|---|---|
| P0-01 | 設計正本化 | v0.4 を `docs/design/` に配置し README 参照を更新 | 対応 | 今後の設計変更は別 PR で扱う |
| P0-02 | Traceability | 初版 matrix を作成し、要求/API/STATIC/BATCH/Data/Infra/UI/Test を分類 | 対応 | 詳細コード証跡は後続 PR で補強 |
| P0-03 | IaC | 現 main は `infra/cloudformation/diopside.yaml` 中心 | 差分あり | `infra/cdk-parity` で CDK synth と contract test を追加 |
| P0-04 | API 基盤 | FastAPI adapter と OpenAPI 3.1 contract を追加。現 deploy entrypoint は Python Lambda handler 中心 | 部分実装 | FastAPI/Mangum 依存同梱と Lambda entrypoint 切替は後続 |
| P0-05 | 管理認証 | HttpOnly cookie + CSRF を追加。Bearer token + CSRF は CLI / automation fallback として維持 | 対応済 | session API と管理 UI cookie 保護を追加済み |
| P0-06 | API-001〜023 | API-001〜023 の handler coverage と OpenAPI contract test を追加。FastAPI adapter は既存 handler へ委譲 | 部分対応 | Pydantic schema 完全化と runtime 切替は後続 |
| P0-07 | STATIC-001〜008 | v0.4 alias path、versioned path、manifest checksum、wordcloud PNG/JSON を static exporter と contract check に追加 | 対応 | SVG は互換 artifact として維持 |
| P0-08 | DDB schema | v0.4 item type と現 repository contract の差分を `docs/design/dynamodb-schema-audit.md` に整理し、主要 writer の current schema を test 化。common metadata、`ChannelRef`、`VideoMonthIndex`、`TagSummary`、`RandomBucket`、`StaticExport` の writer/query path を追加 | 監査済み・差分あり | key prefix / 詳細 schema_version 命名 / 残未対応 item の実装は後続 |
| P0-09 | Worker coverage | BATCH-001〜020 と現 pipeline/handler/job/queue/test の対応を `docs/design/worker-batch-coverage-audit.md` に整理し、job_type / queue mapping を test 化。BATCH-006 は `notification_plan`、BATCH-017 は `archive_finalize` job を追加 | 監査済み・差分あり | 外部通知 delivery、専用 file-output、worker 分割は後続実装 |
| P0-10 | Dev deploy rehearsal | 実 dev 環境で YouTube 実データ 1 件の end-to-end 確認はこの PR では未実施 | 未検証 | credentials と dev stack がある環境で別途実施 |

## 4. P1 / P2 主要差分

| priority | 項目 | 判定 | 補足 |
|---|---|---|---|
| P1 | チャンネル設定管理 | 部分対応 | `GET /api/admin/channels` と `PUT /api/admin/channels/{channel_id}` を追加し、`ChannelRef` read model を保存・優先利用。管理 UI から channel list 読み込みと channel config 更新が可能。既存 data backfill と AppConfig 統合は後続 |
| P1 | タグ補正 | 部分対応 | `PUT /api/admin/videos/{video_id}/tags` で手動タグ追加・削除と static export 反映経路を追加。管理 UI から add/remove/replace を実行可能。tag category/sort order 編集と自動 static export enqueue は未対応 |
| P1 | Archive calendar | 部分対応 | `/data/calendar/{year}.json` と `GET /api/archive-calendar` を追加し、公開 UI で STATIC-005 の月別 chip 表示と year/month 絞り込みに対応。既存 data backfill は未対応 |
| P1 | Presigned URL | 対応 | `POST /api/admin/artifacts/presigned-url` を追加。private S3 artifact のみ署名対象 |
| P1 | NotificationPlan | 部分対応 | 配信 30 分前・開始時刻・archive_available の `NotificationPlan` item を保存。外部通知 delivery は未対応 |
| P1 | file output service | 部分対応 | `file_output` job を追加し、public/private artifact body 出力と `Artifact` item の `artifact_version` / `content_hash` 記録に対応。物理 worker 分割は未対応 |
| P1 | quota rollup | 部分対応 | `quota_rollup` が call record から v0.4 key shape の daily method summary `QuotaUsage` item を保存。threshold warning event は未対応 |
| P1 | wordcloud artifact | 対応 | PNG/JSON alias と versioned path を出力。既存 SVG は互換 artifact として維持 |
| P1 | VideoMonthIndex | 部分対応 | `put_video` が `VideoMonthIndex` item を保存し、archive calendar API/static export が月別 read model を優先利用。既存 data backfill は未対応 |
| P1 | TagSummary | 部分対応 | `put_video` / tag 補正が `TagSummary` item を保存し、API/static export の tag list が read model を優先利用。管理 UI 編集と既存 data backfill は未対応 |
| P1 | RandomBucket | 部分対応 | `put_video` が v0.4 key shape の `RandomBucket` を保存し、`GET /api/random-videos` が seed/count/tag/year で安定抽出。rebuild job と backfill は未対応 |
| P1 | StaticExport history | 部分対応 | `static_export` job が `StaticExport` history item を保存し、管理 API/UI から履歴を表示可能。既存履歴 backfill と superseded 更新は未対応 |
| P1 | timestamp standalone | 対応 | `/data/artifacts/timestamps/{video_id}.json` を出力 |
| P2 | worker 分割 | 差分あり | `static_exporter.pipeline` に複数責務が統合されている |
| P2 | packages 分割 | 差分あり | `packages/domain` や `packages/youtube-client` 分割は未実施 |
| P2 | Next.js static export | 差分あり | 現 main は静的 SPA |
| P2 | FastAPI 移行 | 差分あり | 現 main は hand-written Lambda routing |
| P2 | CDK Construct 化 | 差分あり | 現 main は CloudFormation template |
| P2 | Cost regression | 部分実装 | cost guard 系 tool はあるが v0.4 全観点の継続証跡は未確認 |

## 5. 後続 PR 推奨順

1. `api/fastapi-v04-contract`
   - 既存 route coverage を FastAPI/OpenAPI へ移行し、API-001〜023 の schema 証跡を生成する。
2. `admin/cookie-csrf-session`
   - 対応済。管理 UI の正式保護方式を v0.4 に合わせ、traceability の `NFR-SEC-005` も実装済みに更新した。
3. `worker/batch-v04-coverage`
   - BATCH-001〜020 を job_type、queue、入力/出力 schema、テストに紐付ける。
4. `static/wordcloud-png-artifact`
   - 対応済。v0.4 の `{png|json}` のうち PNG wordcloud を追加し、SVG は互換 artifact として維持する。
5. `infra/cdk-parity`
   - CloudFormation から CDK 正本へ移行する。
6. `web/next-static-export-v04`
   - 現 UI 仕様を維持しつつ Next.js static export へ移行する。

## 6. 未対応・制約・リスク

- この監査は repository 内の README、主要実装、テスト、v0.4 設計書に基づく初版であり、AWS dev 環境や CloudFront 実応答は確認していない。
- traceability の `実装済` は local code/test の証跡に基づく。dev deploy rehearsal や CI green を意味しない。
- v0.4 設計書本文は正本としてコピーし、現 main に合わせた改変は行っていない。
- `docs/` は今回新設であり、既存 `docs/DOCS_STRUCTURE.md` は存在しないため、`docs/design/` 直下に配置した。
