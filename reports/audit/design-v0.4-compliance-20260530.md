# design v0.4 compliance audit

| 項目 | 内容 |
|---|---|
| 作成日 | 2026-05-30 |
| 対象設計 | `docs/design/diopside_basic_design_v0.4.md` |
| 照合対象 | `origin/main` 由来の現 worktree |
| 方針 | v0.4 を正本とし、実装差分は未対応または差分ありとして扱う。 |

## 1. 要約

`.workspace/plan-20260530.txt` の最初の PR 方針に沿って、v0.4 設計書を repository 内に正本化し、現在の `main` 実装との初版 traceability を作成した。

現 main は CloudFront + S3 + Lambda + DynamoDB + SQS + EventBridge という低コスト serverless の大枠に近い。一方で、v0.4 が正本とする Next.js static export、外部通知 delivery などには差分または未対応が残る。AWS CDK は `CfnInclude` による bootstrap app と synth parity contract を追加し、現 CloudFormation template と同じ logical ID / resource type を CDK synth output で検証する段階まで進めた。FastAPI on Lambda は FastAPI adapter / OpenAPI 3.1 contract に加え、Mangum entrypoint、API deploy dependency 同梱、CloudFormation handler 切替まで進め、public GET API-001〜009 と管理 API / 追加 admin route は FastAPI native route + Pydantic response model の baseline に対応した。STATIC-001〜008 は同 PR 内の追加 commit で alias path と manifest checksum の contract 対応を進め、wordcloud は PNG/JSON alias と互換 SVG を出力する。API-007/API-022/API-023 は既存 Lambda handler に追加し、API-008/API-009/API-013/API-015/API-016/API-019 は route contract test を追加した。管理 API の Pydantic request schema 定義と認証・CSRF dependency を含む FastAPI handler 移植は後続課題として残す。ADMIN-SESSION は HttpOnly cookie + CSRF を追加し、CLI / automation 向け Bearer fallback は維持した。DDB schema は v0.4 item type との差分を audit 化し、現 repository contract をテストで固定した。Worker coverage は BATCH-001〜020 の対応を audit 化し、現 pipeline の job_type / queue mapping を contract test で固定した。BATCH-006 は `notification_plan` job、`NotificationPlan` item 作成、due 済み通知の sent/skipped/failed 更新まで、BATCH-017 は `archive_finalize` job として replay collect / static export 投入まで部分実装した。

FR-YT-010 は `chat_normalize` が normalized JSONL を streaming 生成する際に `message_id` で重複除外するよう更新し、chunk をまたいだ同一 message の重複が summary と normalized output に入らないことを `tests/test_core_pipeline.py` で検証した。
BATCH-002 は `YouTubeClient.channels` と `normalize_channel_resource` を追加し、`metadata_sync` が `channels.list` raw response を保存して `Channel` / `ChannelRef` を更新するよう対応した。local test では fake client で channel 情報取得、raw 保存、quota usage、cursor/video 保存を検証した。
BATCH-007 は `chat_collect` mode=`live` が `liveChatMessages.list` を呼び、quota usage、page token requeue、rate limit/offline stop、`ChatPageManifest` 保存を `tests/test_core_pipeline.py` で検証済みのため実装済みに更新した。worker 物理分割は `WORKER-SPLIT` の差分として別管理する。
BATCH-008 は replay initial data / HTML 解析、unknown renderer 保持、continuation 抽出、後続 `chat_collect` job 投入まで対応し、`tests/test_core_pipeline.py` で検証した。
BATCH-009 は replay continuation token から public continuation response を取得する helper と `chat_collect` 分岐を追加し、action 正規化、次 continuation 再投入、`ChatPageManifest` 保存を `tests/test_core_pipeline.py` で検証した。実 YouTube replay continuation response での dev rehearsal は未実施。
BATCH-011 は `chat_normalize` が normalized JSONL を生成する同一 pass で `ChatAggregateAccumulator` により summary JSON、timeline bucket、top terms、author / paid / emoji 統計を生成し、`ChatAggregate` item と `processed/chat-aggregate/.../summary.json` へ保存する。`tests/test_core_pipeline.py` で normalize / aggregate / streaming iterable を検証済みのため機能実装済みに更新した。aggregate 専用 worker の物理分割は `WORKER-SPLIT` の差分として別管理する。
BATCH-013 は `build_timestamp_candidates` の結果から `chapters_suggestion.md` を deterministic に生成し、`rebuild_artifacts` は processed artifact、static export は alias / versioned public artifact と detail JSON 参照を出力するよう更新した。timestamp 専用 worker の物理分割は `WORKER-SPLIT` の差分として別管理する。
BATCH-006 は due 済み `NotificationPlan` について target 未設定時の `skipped`、injected client / SNS delivery 成功時の `sent`、delivery 失敗時の `failed` 更新に対応した。実 SNS/Discord/Email 疎通、物理通知 DLQ、EventBridge one-shot / SQS delay による due 再投入は後続差分として残る。
BATCH-016 は `quota_rollup` が call record から v0.4 key shape の daily method summary を保存し、日次合計が `warning_threshold_units` 以上の場合は `warning_emitted` を保存して `quota_threshold_warning` JobEvent を記録するよう更新した。CloudWatch Alarm 連携は後続差分として残る。
API-020 は互換用の call record `items` に加え、daily summary 由来の `daily`、`by_method`、`limit_per_day`、`warning` を返すよう更新し、管理 UI の quota panel でも warning、daily summary、method summary、call records を表示するよう更新した。

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
| P0-03 | IaC | `infra/cdk/` の CDK app が現 `infra/cloudformation/diopside.yaml` を `CfnInclude` で synth し、resource logical id / type parity を test 化 | 部分実装 | L2 construct 分解、deploy runbook の CDK 基準化、実 deploy rehearsal は後続 |
| P0-04 | API 基盤 | FastAPI adapter、Mangum entrypoint、OpenAPI 3.1 contract、API deploy dependency 同梱、Lambda handler 切替、public GET API-001〜009 と管理 API / 追加 admin route の Pydantic response model baseline を追加 | 部分実装 | 管理 API の Pydantic request schema と認証・CSRF dependency を含む FastAPI handler 移植は後続 |
| P0-05 | 管理認証 | HttpOnly cookie + CSRF を追加。Bearer token + CSRF は CLI / automation fallback として維持 | 対応済 | session API と管理 UI cookie 保護を追加済み |
| P0-06 | API-001〜023 | API-001〜023 と追加 admin route は具体 response schema を追加。API-001〜023 の handler coverage と OpenAPI contract test を追加し、runtime entrypoint は Mangum 経由 | 部分対応 | 管理 API の request schema と FastAPI dependency / handler 移植は後続 |
| P0-07 | STATIC-001〜008 | v0.4 alias path、versioned path、manifest checksum、wordcloud PNG/JSON を static exporter と contract check に追加 | 対応 | SVG は互換 artifact として維持 |
| P0-08 | DDB schema | v0.4 item type と現 repository contract の差分を `docs/design/dynamodb-schema-audit.md` に整理し、主要 writer の current schema を test 化。common metadata、`ChannelRef`、`VideoMonthIndex`、`TagSummary`、`RandomBucket`、`StaticExport` の writer/query path を追加 | 監査済み・差分あり | key prefix / 詳細 schema_version 命名 / 残未対応 item の実装は後続 |
| P0-09 | Worker coverage | BATCH-001〜020 と現 pipeline/handler/job/queue/test の対応を `docs/design/worker-batch-coverage-audit.md` に整理し、job_type / queue mapping を test 化。BATCH-006 は `notification_plan`、BATCH-011 は `chat_normalize` 内 aggregate、BATCH-013 は timestamp JSON / Markdown、BATCH-017 は `archive_finalize` job を追加 | 監査済み・差分あり | 外部通知 delivery、worker 物理分割は後続実装 |
| P0-10 | Dev deploy rehearsal | 実 dev 環境で YouTube 実データ 1 件の end-to-end 確認はこの PR では未実施 | 未検証 | credentials と dev stack がある環境で別途実施 |

## 4. P1 / P2 主要差分

| priority | 項目 | 判定 | 補足 |
|---|---|---|---|
| P1 | チャンネル設定管理 | 部分対応 | `GET /api/admin/channels` と `PUT /api/admin/channels/{channel_id}` を追加し、`ChannelRef` read model を保存・優先利用。管理 UI から channel list 読み込みと channel config 更新が可能。既存 data backfill と AppConfig 統合は後続 |
| P1 | タグ補正 | 部分対応 | `PUT /api/admin/videos/{video_id}/tags` で手動タグ追加・削除と static export 反映経路を追加。管理 UI から add/remove/replace を実行可能。tag category/sort order 編集と自動 static export enqueue は未対応 |
| P1 | Archive calendar | 部分対応 | `/data/calendar/{year}.json` と `GET /api/archive-calendar` を追加し、公開 UI で STATIC-005 の月別 chip 表示と year/month 絞り込みに対応。既存 data backfill は未対応 |
| P1 | Presigned URL | 対応 | `POST /api/admin/artifacts/presigned-url` を追加。private S3 artifact のみ署名対象 |
| P1 | NotificationPlan | 部分対応 | 配信 30 分前・開始時刻・archive_available の `NotificationPlan` item を保存し、due 済み通知の sent/skipped/failed 更新に対応。実 SNS/Discord/Email 疎通、物理通知 DLQ、due 再投入は後続 |
| P1 | file output service | 部分対応 | `file_output` job を追加し、public/private artifact body 出力と `Artifact` item の `artifact_version` / `content_hash` 記録に対応。物理 worker 分割は未対応 |
| P1 | quota rollup | 対応 | `quota_rollup` が call record から v0.4 key shape の daily method summary `QuotaUsage` item を保存し、閾値超過時に `quota_threshold_warning` JobEvent を記録。API-020 と管理 UI は daily/by_method/warning を表示。外部通知 delivery、CloudWatch Alarm は後続 |
| P1 | wordcloud artifact | 対応 | PNG/JSON alias と versioned path を出力。既存 SVG は互換 artifact として維持 |
| P1 | VideoMonthIndex | 部分対応 | `put_video` が `VideoMonthIndex` item を保存し、archive calendar API/static export が月別 read model を優先利用。既存 data backfill は未対応 |
| P1 | TagSummary | 部分対応 | `put_video` / tag 補正が `TagSummary` item を保存し、API/static export の tag list が read model を優先利用。管理 UI 編集と既存 data backfill は未対応 |
| P1 | RandomBucket | 部分対応 | `put_video` が v0.4 key shape の `RandomBucket` を保存し、`GET /api/random-videos` が seed/count/tag/year で安定抽出。rebuild job と backfill は未対応 |
| P1 | StaticExport history | 部分対応 | `static_export` job が `StaticExport` history item を保存し、管理 API/UI から履歴を表示可能。既存履歴 backfill と superseded 更新は未対応 |
| P1 | timestamp standalone | 対応 | `/data/artifacts/timestamps/{video_id}.json` を出力 |
| P2 | worker 分割 | 差分あり | `static_exporter.pipeline` に複数責務が統合されている |
| P2 | packages 分割 | 差分あり | `packages/domain` や `packages/youtube-client` 分割は未実施 |
| P2 | Next.js static export | 差分あり | 現 main は静的 SPA |
| P2 | FastAPI 移行 | 部分実装 | FastAPI/Mangum runtime entrypoint、public GET schema baseline、管理 API response schema baseline は追加済み。管理 route 実装は既存 handler 委譲で、request schema と dependency 移植は後続 |
| P2 | CDK Construct 化 | 部分実装 | `CfnInclude` bootstrap は追加済み。Edge/Data/Api/Collector/Observability construct 分解は後続 |
| P2 | Cost regression | 部分実装 | cost guard 系 tool はあるが v0.4 全観点の継続証跡は未確認 |

## 5. 後続 PR 推奨順

1. `api/fastapi-v04-contract`
   - FastAPI runtime entrypoint、public GET schema baseline、管理 API response schema baseline は追加済み。管理 API の Pydantic request schema と FastAPI dependency / handler 移植を継続する。
2. `admin/cookie-csrf-session`
   - 対応済。管理 UI の正式保護方式を v0.4 に合わせ、traceability の `NFR-SEC-005` も実装済みに更新した。
3. `worker/batch-v04-coverage`
   - BATCH-001〜020 を job_type、queue、入力/出力 schema、テストに紐付ける。
4. `static/wordcloud-png-artifact`
   - 対応済。v0.4 の `{png|json}` のうち PNG wordcloud を追加し、SVG は互換 artifact として維持する。
5. `infra/cdk-parity`
   - CDK bootstrap は追加済み。L2 construct 分解、deploy runbook の CDK 基準化、実 deploy rehearsal を継続する。
6. `web/next-static-export-v04`
   - 現 UI 仕様を維持しつつ Next.js static export へ移行する。

## 6. 未対応・制約・リスク

- この監査は repository 内の README、主要実装、テスト、v0.4 設計書に基づく初版であり、AWS dev 環境や CloudFront 実応答は確認していない。
- traceability の `実装済` は local code/test の証跡に基づく。dev deploy rehearsal や CI green を意味しない。
- v0.4 設計書本文は正本としてコピーし、現 main に合わせた改変は行っていない。
- `docs/` は今回新設であり、既存 `docs/DOCS_STRUCTURE.md` は存在しないため、`docs/design/` 直下に配置した。
