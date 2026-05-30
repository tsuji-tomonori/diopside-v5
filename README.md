# diopside v5

`diopside` は、白雪巴 YouTube 公開アーカイブを低コストに検索・閲覧し、公開チャットからワードクラウドとタイムスタンプ候補を生成する serverless アプリケーションです。設計根拠は `docs/design/diopside_basic_design_v0.4.md` です。

## 全体構成

- Public UI: `apps/web/public` を S3 + CloudFront で静的配信する。
- Public data: `apps/workers/static-exporter` が DynamoDB/S3 read model から `/data/latest-manifest.json` と `/data/v/{export_version}/public/...` を生成する。
- API: `apps/api` の Python Lambda handler が CloudFront `/api/*` 経由で public API と HttpOnly cookie + CSRF 付き管理 API を提供する。CLI / automation 向け Bearer fallback も維持する。
- Worker: `static_exporter.pipeline` が metadata sync、live status scan、chat collect、chat normalize、artifact rebuild、retry/cancel、quota rollup、cleanup を SQS 経由で実行する。`static_exporter.handler` は static export job を実行する。
- Storage: DynamoDB single-table を小さな正本、S3 を raw/processed/public artifact の正本にする。
- 採用しないもの: SQL 系 DB、OpenSearch、ECS、EC2、常時起動サーバー。

## CloudFront path 設計

| Path | Origin | Cache |
|---|---|---|
| `/`, SPA route | Web S3 | immutable 相当。SPA rewrite で `/index.html` に集約 |
| `/assets/*` | Web S3 | 長 TTL |
| `/data/latest-manifest.json` | Public data S3 | 短 TTL |
| `/data/v/*` | Public data S3 | 長 TTL immutable |
| `/api/*` | Lambda Function URL origin via CloudFront OAC | no-store/no-cache |

S3 origin は REST origin + OAC と bucket policy で CloudFront 経由の `s3:GetObject` に限定します。`WebBucket` と `PublicDataBucket` は public access block を有効にし、bucket policy は `cloudfront.amazonaws.com` principal、対象 distribution の `AWS:SourceArn`、`s3:GetObject` のみを許可します。
API の利用者向け endpoint は CloudFront の `ApiEndpoint` output です。Lambda Function URL は `AWS_IAM` + CloudFront OAC で保護された internal origin で、ブラウザ・運用スクリプト・管理UIから直接呼びません。
CloudFront behavior は上から `/api/*`、`/data/latest-manifest.json`、`/data/v/*`、`/assets/*` の順に評価し、template contract test で origin と cache policy を検証します。post-deploy smoke は CloudFront 経由で `/`、静的 asset、manifest、versioned public data、API を取得し、API の no-store header と CloudFront 経由 header を確認します。

## DynamoDB item schema

物理 key は `pk` / `sk`、GSI は `by_public_date`、`by_tag`、`by_work_queue` です。実装は `apps/shared/src/diopside_core/repository.py` に集約しています。公開動画、job 一覧、quota usage 一覧は DynamoDB `scan` を使わず、公開動画は `by_public_date`、job/quota 一覧は `by_work_queue` の Query + pagination で取得します。
repository writer は保存時に共通 metadata として `schema_version`、`entity_id`、`created_at`、`updated_at` を付与します。既存 item の `created_at` と明示指定された `schema_version` / `entity_id` は上書きしません。

v0.4 正本との差分は `docs/design/dynamodb-schema-audit.md` に整理しています。現 repository は single-table と S3 退避方針は近い一方、key prefix や item type ごとの詳細 schema version 命名などに未対応または差分があります。`ChannelRef`、`VideoMonthIndex`、`NotificationPlan`、`TagSummary`、`RandomBucket`、`StaticExport` は v0.4 key shape で部分実装しています。

| item_type | pk | sk | 主な用途 |
|---|---|---|---|
| `AppConfig` | `APP#CONFIG` | `META` | アプリ全体設定。`target_channel_ids`、`youtube_api_key_ssm_param`、collection/export flags を保持し、旧 `CONFIG#app` は読み取り fallback |
| `Channel` | `CH#{channel_id}` | `META` | 対象チャンネル。`channel_title`、`uploads_playlist_id`、`collect_enabled`、`default_tags` を保持し、旧 `CHANNEL#{channel_id}` は読み取り fallback |
| `ChannelRef` | `APP#CHANNELS` | `CH#{channel_id}` | 管理チャンネル一覧 read model。`Channel` 更新時に同期し、一覧取得で優先利用 |
| `ChannelSyncCursor` | `CH#{channel_id}` | `CURSOR#uploads` | uploads playlist 差分位置。`next_page_token`、raw response URI、取得 video ids を保持し、旧 `ChannelCursor` / `CHANNEL#{channel_id}` は読み取り fallback |
| `Video` | `VID#{video_id}` | `META` | 公開動画 metadata。公開対象のみ `by_public_date` に `PUB#{inverted_published_at}#{video_id}` で投影し、旧 `VIDEO#{video_id}` は読み取り fallback |
| `VideoIndex` | `VIDEO#PUBLIC` | `PUB#{inverted_published_at}#{video_id}` | 公開日順 index 用 |
| `VideoStateEvent` | `VID#{video_id}` | `EVT#STATE#{occurred_at}#{event_id}` | live/archive 状態遷移履歴。`live_status_scan` / `archive_finalize` が append |
| `VideoStatSnapshot` | `VID#{video_id}` | `STAT#{yyyyMMddHH}` | view/like/comment などの低頻度統計 snapshot。metadata 統計取得時に upsert |
| `VideoTagIndex` | `TAG#{tag}` | `VIDEO#{video_id}` | tag 絞り込み |
| `VideoTagLink` | `VID#{video_id}` | `TAG#{tag_id}` | v0.4 tag link read model。`tag_label`、`tag_type`、`source`、`gsi2pk=TAG#{tag_id}` を保持し、既存 `VideoTagIndex` も互換維持 |
| `VideoMonthIndex` | `VID#{video_id}` | `INDEX#MONTH#{yyyyMM}` | archive calendar 用 read model。`by_public_date` の `VIDEO#MONTH#{yyyyMM}` で月別取得 |
| `TagSummary` | `TAG#{tag_id}` | `META` | tag list read model。`video_count`、latest video、category、public visibility を保持 |
| `ChatManifest` | `VID#{video_id}` | `CHAT#MANIFEST` | normalized JSONL manifest。collection/normalization state と `normalized_s3_uri` を保持し、旧 `VIDEO#{video_id}` は読み取り fallback |
| `ChatPageManifest` | `VID#{video_id}` | `CHAT#PAGE#{source}#{seq}` | raw page manifest。`raw_s3_uri`、`item_count`、`checksum`、offset範囲、`next_poll`のみを持ち、チャット本文は保存しない。旧 `ChatMessageChunkManifest` / `VIDEO#{video_id}` は読み取り fallback |
| `ChatAggregate` | `VID#{video_id}` | `CHAT#AGG#v1` | 集計 summary/top_terms/timeline。旧 `VIDEO#{video_id}` / `CHAT#AGGREGATE` は読み取り fallback |
| `Artifact` | `VID#{video_id}` | `ARTIFACT#{type}#{version}` | wordcloud/timestamp public path。`artifact_version` と `content_hash` を保持し、旧 `VIDEO#{video_id}` item は読み取り fallback |
| `Job` | `JOB#{job_id}` | `META` | job metadata と `dedupe_key` / `idempotency_key`。`latest_state` ごとに `JOB#STATE#{latest_state}` として `by_work_queue` に投影し、旧 `JOB#ALL` は一覧 fallback |
| `JobEvent` | `JOB#{job_id}` | `EVT#{seq}` | append-only job event。`event_name` / `state_after` / `occurred_at` / `payload` を正本とし、既存 API/UI 互換のため `event_type` / `details` alias も保持 |
| `Idempotency` | `IDEMP#{dedupe_key}` | `META` | job 起動の冪等 read model。`first_job_id`、`request_hash`、互換 `idempotency_key` を保持 |
| `QuotaUsage` call record | `QUOTA#{yyyy-mm-dd}` | `{time}#{method}#{uuid}` | YouTube quota 呼び出し記録。`record_type=call` とし、`by_work_queue` に `QUOTA#ALL` として投影 |
| `QuotaUsage` daily summary | `QUOTA#{yyyyMMdd}` | `METHOD#{method}` | BATCH-016 が保存する v0.4 形状の日別・method別 summary。`call_count`、`units_used`、`unit_per_call` を保持 |
| `Lock` | `LOCK#{lock_key}` | `META` | TTL付き二重実行制御。`owner_job_id`、任意の `owner_request_id`、`acquired_at`、UNIX epoch seconds の `expires_at` を保持 |
| `RandomBucket` | `RANDOM#DEFAULT` | `VID#{bucket_no}#{video_id}` | random API 用の事前 bucket。公開 `put_video` 時に upsert し、非公開化で削除 |
| `StaticExport` | `EXPORT#public` | `VERSION#{exported_at}` | public data export 履歴。manifest URI、prefix、件数、schema versions、content hash、publish state を保持 |

job は `idempotency_key` から安定した `job_id` を導出し、DynamoDB では `attribute_not_exists(pk)` の条件付き書き込みで同じ key の二重起動を避けます。状態は `Job` item の保存値ではなく、`JobEvent` の末尾イベントから導出します。

## S3 path 設計

- `raw/youtube/metadata/channel_id={channel_id}/playlistItems/{time}.json`: `playlistItems.list` raw response。
- `raw/youtube/metadata/channel_id={channel_id}/videos/{time}.json`: `videos.list` raw response。
- `raw/youtube/chat/...`: YouTube live/replay chat raw response。
- `processed/chat-normalized/video_id={video_id}/part-000.jsonl`: 正規化チャット。
- `processed/chat-aggregate/video_id={video_id}/summary.json`: 集計。
- `data/latest-manifest.json`: 最新 export への差し替え manifest。
- `data/home.json`: v0.4 STATIC-001 の最新 home alias。
- `data/videos/index.json`: v0.4 STATIC-002 の最新動画一覧 alias。
- `data/videos/{video_id}.json`: v0.4 STATIC-003 の最新動画詳細 alias。
- `data/tags.json`: v0.4 STATIC-004 の最新 tag alias。
- `data/calendar/{year}.json`: v0.4 STATIC-005 の年/月別 calendar alias。
- `data/v/{export_version}/public/index/videos-latest.json`: 最新一覧。
- `data/v/{export_version}/public/index/tags.json`: tag index。
- `data/v/{export_version}/public/search/videos-{year}.json`: 年別検索 index。
- `data/v/{export_version}/public/calendar/{year}.json`: 年/月別 calendar の immutable 実体。
- `data/v/{export_version}/public/videos/{video_id}.json`: 動画詳細。
- `data/artifacts/wordcloud/{video_id}.png`: v0.4 STATIC-007 の最新 PNG wordcloud alias。
- `data/v/{export_version}/public/artifacts/wordcloud/{video_id}.png`: v0.4 STATIC-007 の PNG wordcloud 実体。
- `data/v/{export_version}/public/artifacts/wordcloud/{video_id}.svg`: 互換 SVG wordcloud。
- `data/v/{export_version}/public/artifacts/wordcloud/{video_id}.json`: v0.4 STATIC-007 の wordcloud JSON 実体。
- `data/v/{export_version}/public/artifacts/timestamps/{video_id}.json`: v0.4 STATIC-008 の timestamp JSON 実体。
- `data/v/{export_version}/public/artifacts/timestamps/{video_id}.md`: BATCH-013 の chapters suggestion Markdown 実体。

Raw/processed artifact は個人開発向けの保持期間を CDK synth 対象の CloudFormation lifecycle で定義します。

| Prefix | Bucket | Transition | Expiration | 用途 |
|---|---|---:|---:|---|
| `raw/youtube/metadata/` | `RawBucket` | 90日で `STANDARD_IA` | 365日 | `playlistItems.list` / `videos.list` raw response |
| `raw/youtube/chat/` | `RawBucket` | 30日で `STANDARD_IA` | 180日 | live/replay chat raw JSONL |
| `failed/` | `RawBucket` | なし | 90日 | failed debug artifact |
| `processed/chat-normalized/` | `ProcessedBucket` | 90日で `STANDARD_IA` | 730日 | 正規化チャット JSONL |
| `processed/chat-aggregate/` | `ProcessedBucket` | 90日で `STANDARD_IA` | 730日 | 集計 summary |

Public data の `/data/v/{export_version}/public/...` は immutable export として扱い、manifest 差し替え契約を壊さないよう Raw/Processed の lifecycle とは分けて管理します。

`tools/check-public-contract.mjs` は local fixture、static exporter output、post-deploy smoke で取得した public data に対して、manifest/index/search/detail/tag の schema、versioned path、v0.4 STATIC-001〜008 alias path、manifest checksum、wordcloud artifact 実体、timestamp candidate field の整合性を検証します。

static export は `ChatAggregate.top_terms` がある動画だけ deterministic な PNG wordcloud と互換 SVG wordcloud を生成し、動画詳細 JSON の `chat_summary.wordcloud_url` と `artifacts.wordcloud` から PNG alias と versioned path を参照できるようにします。`top_terms` がない動画では fake/empty PNG/SVG を生成せず、`wordcloud_url` と `artifacts.wordcloud` は `null` にします。
timestamp 候補は JSON に加えて `/data/artifacts/timestamps/{video_id}.md` と versioned Markdown を生成し、動画詳細 JSON の `artifacts.timestamp_chapters` から参照できます。

S3 upload 時は `/data/v/{export_version}/public/...` の versioned data を先に upload し、最後に `/data/latest-manifest.json` を upload します。versioned data の upload 途中で失敗した場合は manifest を差し替えないため、既存の公開 export_version は維持されます。
`/data/home.json` などの alias JSON も manifest より先に upload します。`latest-manifest.json` の `static_paths` には STATIC-001〜008 ごとの alias path、対応する versioned path、alias file の `checksum_sha256` を入れます。`/data/artifacts/wordcloud/{video_id}.png` と `/data/artifacts/wordcloud/{video_id}.json` は v0.4 の STATIC-007 artifact として正式出力し、既存 SVG wordcloud は互換 artifact として維持します。

## 環境変数

| 変数 | 用途 |
|---|---|
| `DIOPSIDE_TABLE_NAME` | DynamoDB table |
| `DIOPSIDE_PUBLIC_DATA_BUCKET` | public data S3 bucket |
| `DIOPSIDE_PUBLIC_DATA_PREFIX` | public data prefix。既定 `data` |
| `DIOPSIDE_ADMIN_TOKEN` | 管理 API session passphrase と CLI / automation 用 Bearer fallback token |
| `DIOPSIDE_ADMIN_SESSION_SECRET` | 管理 API session cookie 署名 secret。未設定時は `DIOPSIDE_ADMIN_TOKEN` を利用 |
| `DIOPSIDE_ADMIN_CSRF_TOKEN` | CLI / automation 用 Bearer fallback CSRF token |
| `DIOPSIDE_METADATA_QUEUE_URL` | metadata/live-status/retry/cancel queue |
| `DIOPSIDE_CHAT_QUEUE_URL` | chat collect queue |
| `DIOPSIDE_NORMALIZE_QUEUE_URL` | chat normalize queue |
| `DIOPSIDE_AGGREGATE_QUEUE_URL` | artifact rebuild queue |
| `DIOPSIDE_STATIC_EXPORT_QUEUE_URL` | static export queue |
| `YOUTUBE_API_KEY` または `DIOPSIDE_YOUTUBE_API_KEY` | YouTube Data API key |
| `DIOPSIDE_ALLOW_DRY_RUN_JOBS` | local 検証専用の dry-run job 許可 |

GitHub Actions から手動 job を投入する場合は、repository secret `DIOPSIDE_GITHUB_ACTIONS_ROLE_ARN` と各 queue URL secret（`DIOPSIDE_METADATA_QUEUE_URL`、`DIOPSIDE_CHAT_QUEUE_URL`、`DIOPSIDE_NORMALIZE_QUEUE_URL`、`DIOPSIDE_AGGREGATE_QUEUE_URL`、`DIOPSIDE_STATIC_EXPORT_QUEUE_URL`）を設定します。`.github/workflows/manual-job-dispatch.yml` は GitHub OIDC で AWS role を引き受け、v0.4 `JobMessage` schema の SQS message を送ります。

YouTube API key は CloudFormation の `YouTubeApiKey` NoEcho parameter から `WorkerFunction` の `DIOPSIDE_YOUTUBE_API_KEY` へ渡します。コードや template default には直書きしません。local 実行では `YOUTUBE_API_KEY` または `DIOPSIDE_YOUTUBE_API_KEY` を使えます。

## IAM権限境界

Lambda の実行 role は職務ごとに分離します。

| Role | 対象 | 主な権限境界 |
|---|---|---|
| `ApiRole` | `ApiFunction` | 管理 job enqueue の `sqs:SendMessage`、public/admin read model 用の DynamoDB read/write、PublicDataBucket の `s3:GetObject` |
| `StaticExporterRole` | `StaticExporterFunction` | static export 用の DynamoDB read/write、PublicDataBucket の `s3:GetObject` / `s3:PutObject`、`StaticExportQueue` の consume |
| `WorkerRole` | `WorkerFunction` | worker queue の consume、各 job の再投入用 `sqs:SendMessage`、Raw/Processed bucket の `s3:GetObject` / `s3:PutObject`、DynamoDB read/write |
| `SchedulerRole` | EventBridge Scheduler | `MetadataQueue` / `AggregateQueue` への `sqs:SendMessage` のみ |

`StaticExporterRole` は Raw/Processed bucket へアクセスせず、`WorkerRole` は PublicDataBucket へ書き込みません。どの role も `s3:*`、`sqs:*`、`dynamodb:*` は使わず、必要な action を列挙します。将来の分離方針として、worker の job type が増えた場合は metadata/chat/normalize/aggregate を別 Lambda + 別 role に分け、queue consume と S3 prefix をさらに狭めます。

## 実装済み API と schema

`apps/api/src/diopside_api/handler.py` が現在実装している API route は次の通りです。`tools/check-docs-consistency.mjs` はこの表と実装済み schema_version の対応を `npm test` で検証します。
`apps/api/src/diopside_api/openapi_contract.py` は API-001〜023 と追加管理 route の OpenAPI 3.1 contract を依存なしで生成します。`apps/api/src/diopside_api/fastapi_app.py` は FastAPI adapter として既存 `lambda_handler` へ委譲します。deploy package は `requirements-api.txt` の FastAPI / Mangum 依存を `api.zip` に同梱し、Lambda entrypoint は `diopside_api.fastapi_lambda.lambda_handler` を使います。`GET /api/health`、`GET /api/config`、`GET /api/home`、`GET /api/videos`、`GET /api/tags` は FastAPI native route + Pydantic response model の baseline に対応済みです。残 API の Pydantic request / response schema 定義は後続対象です。

| API | schema_version | 内容 |
|---|---|---|
| `GET /api/health` | なし | service status と任意の dependency status |
| `GET /api/config` | `public-config/v1` | public client 設定 |
| `GET /api/home` | `public-home/v1` | latest videos と popular tags |
| `GET /api/videos` | `public-video-list/v1` | public video list。`q` / `tag` / `limit` で絞り込み |
| `GET /api/tags` | `public-tag-list/v1` | tag list |
| `GET /api/archive-calendar` | `public-archive-calendar/v1` | year/month query による archive calendar |
| `GET /api/random-videos` | `public-random-videos/v1` | `RandomBucket` を seed / count / tag / year で安定抽出した random video list |
| `GET /api/videos/{video_id}` | `public-video-detail/v1` | video detail と chat summary |
| `GET /api/videos/{video_id}/artifacts` | `public-video-artifacts/v1` | video artifact list |
| `POST /api/admin/session` | `admin-session/v1` | 管理 session cookie と CSRF token を発行 |
| `GET /api/admin/me` | `admin-session/v1` | 管理 session と CSRF token を確認 |
| `GET /api/admin/jobs` | `admin-job-list/v1` | 管理 job list |
| `GET /api/admin/jobs/{job_id}` | `admin-job-detail/v1` | 管理 job detail と events |
| `GET /api/admin/channels` | `admin-channel-list/v1` | channel list |
| `GET /api/admin/quota-usage` | `admin-quota-usage/v1` | quota usage call records、daily summary、method summary、warning |
| `GET /api/admin/static-exports` | `admin-static-export-list/v1` | static export history list |
| `PUT /api/admin/channels/{channel_id}` | `admin-channel-config/v1` | channel config を更新 |
| `PUT /api/admin/videos/{video_id}/tags` | `admin-video-tags/v1` | 動画の手動タグ追加・削除 |
| `POST /api/admin/artifacts/presigned-url` | `admin-artifact-presigned-url/v1` | private S3 artifact の短時間署名 URL を発行 |
| `POST /api/admin/jobs/metadata-sync` | job accepted response | `metadata_sync` を enqueue |
| `POST /api/admin/jobs/live-status-scan` | job accepted response | `live_status_scan` を enqueue |
| `POST /api/admin/jobs/chat-collect` | job accepted response | `chat_collect` を enqueue |
| `POST /api/admin/jobs/chat-normalize` | job accepted response | `chat_normalize` を enqueue |
| `POST /api/admin/jobs/rebuild-artifacts` | job accepted response | `rebuild_artifacts` を enqueue |
| `POST /api/admin/jobs/static-export` | job accepted response | `static_export` を enqueue |
| `POST /api/admin/jobs/{job_id}/retry` | job accepted response | `retry_job` を enqueue |
| `POST /api/admin/jobs/{job_id}/cancel` | job accepted response | `cancel_job` を enqueue |

公開 UI は `latest-manifest.json` から動画一覧、タグ、STATIC-005 の月別 calendar JSON を読み込み、検索、タグ、年/月、長さ、成果物有無で絞り込みできます。月別アーカイブの chip を選ぶと該当 year/month を filter sheet と同期し、公開動画一覧を同じ条件で絞り込みます。

管理 UI は `POST /api/admin/session` で `DIOPSIDE_ADMIN_TOKEN` 相当の passphrase を検証し、HttpOnly / Secure / SameSite=Lax の session cookie と `csrf_token` を受け取ります。管理 GET は cookie session だけで利用でき、管理 PUT/POST は cookie session と `X-CSRF-Token` を必須にします。CLI / automation は従来通り `Authorization: Bearer <DIOPSIDE_ADMIN_TOKEN>` と `X-CSRF-Token: <DIOPSIDE_ADMIN_CSRF_TOKEN>` を fallback として利用できます。管理 UI では job 起動・job 詳細・quota usage daily/method summary、static export 履歴に加え、channel list の読み込みと `channel_id`、`uploads_playlist_id`、`display_name`、取得有効/無効、通知候補生成、metadata/live scan interval の更新、動画タグの追加・削除・置換ができます。job 起動系 API は body または `X-Idempotency-Key` で `idempotency_key` を必須にし、同じ key の二重起動を repository で抑止します。`PUT /api/admin/videos/{video_id}/tags` は `add_tags` / `remove_tags` / `replace_tags` で `Video.tags` と `VideoTagIndex` を更新し、次回 static export で `/data/tags.json` と動画詳細 JSON へ反映します。`POST /api/admin/artifacts/presigned-url` は `s3://` の private artifact だけを対象にし、`raw/`、`processed/`、`failed/` prefix 以外や public path には署名 URL を発行しません。

## public data schema

`apps/workers/static-exporter/src/static_exporter/handler.py` が生成する tracked public data path と schema_version は次の通りです。

| Path | schema_version | 内容 |
|---|---|---|
| `/data/latest-manifest.json` | `public-manifest/v1` | 最新 export_version と index path |
| `/data/home.json` | `public-home/v1` | 最新 home summary alias |
| `/data/videos/index.json` | `public-video-list/v1` | 最新 video list alias |
| `/data/videos/{video_id}.json` | `public-video-detail/v1` | 最新 video detail alias |
| `/data/tags.json` | `public-tag-list/v1` | tag list alias |
| `/data/calendar/{year}.json` | `public-archive-calendar/v1` | 年/月別 calendar alias |
| `/data/artifacts/wordcloud/{video_id}.png` | PNG | wordcloud image alias |
| `/data/artifacts/wordcloud/{video_id}.json` | `public-wordcloud/v1` | wordcloud top terms JSON alias |
| `/data/artifacts/timestamps/{video_id}.json` | `public-timestamp-list/v1` | timestamp candidate list alias |
| `/data/artifacts/timestamps/{video_id}.md` | Markdown | chapters suggestion alias |
| `/data/v/{export_version}/public/index/videos-latest.json` | `public-video-list/v1` | 最新 video list |
| `/data/v/{export_version}/public/index/tags.json` | `public-tag-list/v1` | tag list |
| `/data/v/{export_version}/public/search/videos-{year}.json` | `public-video-search/v1` | 年別 search index |
| `/data/v/{export_version}/public/calendar/{year}.json` | `public-archive-calendar/v1` | 年/月別 calendar |
| `/data/v/{export_version}/public/videos/{video_id}.json` | `public-video-detail/v1` | video detail、chat summary、artifact、timestamp |
| `/data/v/{export_version}/public/artifacts/wordcloud/{video_id}.png` | PNG | deterministic wordcloud artifact |
| `/data/v/{export_version}/public/artifacts/wordcloud/{video_id}.svg` | SVG | compatibility wordcloud artifact |
| `/data/v/{export_version}/public/artifacts/wordcloud/{video_id}.json` | `public-wordcloud/v1` | wordcloud top terms JSON |
| `/data/v/{export_version}/public/artifacts/timestamps/{video_id}.json` | `public-timestamp-list/v1` | timestamp candidate list |
| `/data/v/{export_version}/public/artifacts/timestamps/{video_id}.md` | Markdown | chapters suggestion |

## 運用 job

| API | job_type | 内容 |
|---|---|---|
| `POST /api/admin/jobs/metadata-sync` | `metadata_sync` | uploads playlist と `videos.list` による metadata 同期 |
| `POST /api/admin/jobs/live-status-scan` | `live_status_scan` | upcoming/live/archived 判定 |
| `POST /api/admin/jobs/chat-collect` | `chat_collect` | live/replay chat chunk 収集 |
| `POST /api/admin/jobs/chat-normalize` | `chat_normalize` | normalized JSONL と aggregate 生成 |
| `POST /api/admin/jobs/rebuild-artifacts` | `rebuild_artifacts` | wordcloud/timestamp 再生成 |
| worker internal | `file_output` | public/private artifact body を S3/local に出力し `Artifact` item を記録 |
| `POST /api/admin/jobs/static-export` | `static_export` | public JSON/artifact export |
| `POST /api/admin/jobs/{job_id}/retry` | `retry_job` | failed/retryable job に `retry_requested` event を追加し、元 job type の queue へ再投入 |
| `POST /api/admin/jobs/{job_id}/cancel` | `cancel_job` | 未完了 job に `cancelled` event を追加。完了済み/失敗済み job は拒否 |

CloudFormation では EventBridge Scheduler から低頻度の定期 job を SQS へ投入します。`metadata_sync` は 12 時間ごと、`live_status_scan` は 30 分ごとに `MetadataQueue` へ投入し、`quota_rollup` は 1 日ごと、`cleanup` は 7 日ごとに `AggregateQueue` へ投入します。`notification_plan` は `live_status_scan` が upcoming 動画を検知したときに `before_30min` / `at_start` の `NotificationPlan` item を作成します。due 済み通知は target 未設定なら `skipped`、injected client または SNS delivery 成功なら `sent`、失敗なら `failed` に更新します。`archive_finalize` は `live_status_scan` が `upcoming` / `live` から `archived` への遷移を検知したときに `AggregateQueue` へ投入し、`archive_available` の `NotificationPlan`、replay `chat_collect`、`static_export` を後続投入します。Scheduler 用 IAM role は `MetadataQueue` / `AggregateQueue` への `sqs:SendMessage` のみに制限します。`cleanup` は現時点では常に dry-run report を返し、削除は実行しません。

worker が dispatch する job_type は `metadata_sync`、`live_status_scan`、`chat_collect`、`chat_normalize`、`rebuild_artifacts`、`file_output`、`archive_finalize`、`notification_plan`、`static_export`、`retry_job`、`cancel_job`、`quota_rollup`、`cleanup` です。管理 API、EventBridge Scheduler、GitHub Actions `workflow_dispatch`、worker の後続投入は v0.4 `JobMessage` に合わせ、`job_id`、`job_type`、`idempotency_key`、`requested_by`、`attempt`、`trace_id`、`payload` を持つ message を送ります。worker dispatch は旧 `input` message も読み取り互換として受け付けます。`file_output` は BATCH-014 の public/private artifact 出力を担当し、`Artifact` item に `artifact_version`、`content_hash`、`generated_at` を記録します。`static_export` は `static_exporter.handler` で public JSON/artifact を生成し、それ以外は `static_exporter.pipeline` で処理します。

BATCH-001〜020 と現 worker 実装の差分は `docs/design/worker-batch-coverage-audit.md` に整理しています。現状は統合 pipeline で主要経路を処理しており、実 SNS/Discord/Email 疎通、file-output の物理 worker 分割、worker 分割責務には未対応または差分があります。

## DLQ運用手順

CloudFormation では各 worker queue に `maxReceiveCount=3` の redrive policy を設定し、3 回処理に失敗した message を対応する DLQ へ移動します。

| 元queue | DLQ | 主なjob |
|---|---|---|
| `MetadataQueue` | `MetadataDlq` | `metadata_sync`、`live_status_scan`、`retry_job`、`cancel_job` |
| `ChatQueue` | `ChatDlq` | `chat_collect` |
| `NormalizeQueue` | `NormalizeDlq` | `chat_normalize` |
| `AggregateQueue` | `AggregateDlq` | `rebuild_artifacts`、`file_output`、`archive_finalize`、`notification_plan`、`quota_rollup`、`cleanup` |
| `StaticExportQueue` | `StaticExportDlq` | `static_export` |

DLQ depth は CloudWatch metric `AWS/SQS ApproximateNumberOfMessagesVisible` で確認します。CLI で確認する場合は、対象 stack の logical resource id から queue URL を特定し、`ApproximateNumberOfMessages` と `ApproximateNumberOfMessagesNotVisible` を確認します。

```sh
DLQ_URL=$(aws cloudformation describe-stack-resource \
  --stack-name diopside-prod \
  --logical-resource-id MetadataDlq \
  --query 'StackResourceDetail.PhysicalResourceId' \
  --output text)

aws sqs get-queue-attributes \
  --queue-url "$DLQ_URL" \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
```

原因調査では、まず DLQ message を 1 件だけ短い visibility timeout で確認し、`job_id`、`job_type`、`input`、`retry_of` を控えます。次に `GET /api/admin/jobs/{job_id}` または DynamoDB の `JobEvent` を確認し、最後の `failed` event の `message` と `debug_uri` を確認します。`debug_uri` がある場合は Raw/processed bucket の failed debug artifact を取得し、例外型、入力 payload、外部 API の応答分類を確認します。

```sh
aws sqs receive-message \
  --queue-url "$DLQ_URL" \
  --max-number-of-messages 1 \
  --visibility-timeout 30 \
  --attribute-names All \
  --message-attribute-names All
```

再投入は、原因が解消済みで同じ payload を再実行しても安全な場合だけ行います。推奨は管理 API の `POST /api/admin/jobs/{job_id}/retry` で、`retry_requested` event を残して元 job type の queue へ再投入する方法です。DLQ message を直接元 queue へ送るのは、`JobEvent` と管理画面の追跡が崩れないことを確認できる緊急時に限定します。直接再投入した場合も、操作前後の DLQ message id、job_id、理由、投入先 queue を作業メモまたは PR/incident report に残します。

破棄は、message が古い deploy 由来、入力データが修復不能、または再投入で重複副作用が出ると判断できる場合だけ実施します。破棄前に message body、message id、job_id、debug_uri、判断理由を記録し、必要な raw/debug artifact を保存します。CLI で破棄する場合は `receive-message` で得た `ReceiptHandle` を使って 1 件ずつ削除し、bulk purge は同一原因の大量滞留で全件破棄が妥当と確認できる場合だけ使います。

```sh
aws sqs delete-message \
  --queue-url "$DLQ_URL" \
  --receipt-handle "<receipt-handle>"
```

再投入後は、元 queue の visible/not visible 数、DLQ depth、対象 job の `JobEvent`、関連 S3 artifact、`GET /api/admin/jobs/{job_id}` の `derived_state` を確認します。再発防止では、失敗分類が入力 validation、YouTube quota/rate limit、S3/DynamoDB permission、parser schema drift、artifact contract failure のどれかを切り分け、必要に応じて unit test、contract test、README 手順、CloudWatch Alarm の閾値を更新します。

## CloudWatch JSONログ

API と worker は CloudWatch Logs で検索しやすいように、標準出力へ 1 行 JSON を出力します。payload 全体、管理 token、CSRF token、YouTube API key は log に出しません。

| component | event | 主なfield |
|---|---|---|
| `api` | `api_request` | `trace_id`、`method`、`path`、`status`、`result`、`duration_ms`、`job_id`、`job_type`、`video_id`、`error` |
| `worker` | `worker_job` | `trace_id`、`job_id`、`job_type`、`video_id`、`result`、`duration_ms`、`error` |

`trace_id` は API request の `x-trace-id` header を優先し、未指定時は `trc_...` を生成します。管理 API が SQS に投入する worker payload には同じ `trace_id` を含めるため、CloudWatch Logs Insights では API と worker を同じ trace で追跡できます。`job_id` が分かる場合は `GET /api/admin/jobs/{job_id}` と `JobEvent`、failed debug artifact の `debug_uri` を合わせて確認します。

CloudWatch Logs Insights での調査例:

```sql
fields @timestamp, component, event, trace_id, job_id, job_type, video_id, result, duration_ms, error
| filter trace_id = "trc_xxx" or job_id = "job_xxx"
| sort @timestamp asc
```

error 調査では `result="failed"` を起点にし、API では `status` と `error.code`、worker では `error.type` と `error.debug_uri` を確認します。duration の外れ値調査では `duration_ms` の降順で API path または worker job type を絞り込みます。

## CloudWatch Alarm

CloudFormation は最低限の alarm を作成します。初期構成では個人開発向けに通知先を固定せず、alarm action は未設定です。通知が必要な場合は deploy 後に SNS topic や ChatOps 連携を追加し、同じ alarm resource に action を関連付けます。

| Alarm | 対象 | 発火条件 | 初動 |
|---|---|---|---|
| `MetadataDlqDepthAlarm` / `ChatDlqDepthAlarm` / `NormalizeDlqDepthAlarm` / `AggregateDlqDepthAlarm` / `StaticExportDlqDepthAlarm` | 各 DLQ | `ApproximateNumberOfMessagesVisible >= 1` | DLQ 運用手順に従い message、`job_id`、`debug_uri` を確認 |
| `ApiFunctionErrorsAlarm` | API Lambda | `AWS/Lambda Errors >= 1` | CloudWatch JSON log の `trace_id` と ErrorResponse を確認 |
| `WorkerFunctionErrorsAlarm` | worker Lambda | `AWS/Lambda Errors >= 1` | `job_id`、`JobEvent`、failed debug artifact を確認 |
| `StaticExportFailureAlarm` | static export Lambda | `AWS/Lambda Errors >= 1` | static export job の event、public data manifest 差し替え有無、artifact upload を確認 |
| `Api5xxAlarm` | API JSON log metric filter | `Api5xxCount >= 1` | `component=api`、`status >= 500` の log を `trace_id` で追跡 |

Function URL origin では API Gateway の 5xx metric を使わないため、`Api5xxAlarm` は API の 1 行 JSON log から `Api5xxCount` metric を作ります。alarm が発火した場合は、まず該当時間帯の CloudWatch Logs Insights で `result="failed"`、`trace_id`、`job_id` を絞り込み、必要に応じて DLQ depth、JobEvent、failed debug artifact を合わせて確認します。

## quota 節約方針

- 通常巡回では `search.list` を使わず、uploads playlist の `playlistItems.list` と `videos.list` を使う。
- `metadata_sync` は明示 `page_token` がなければ `ChannelSyncCursor.next_page_token` から再開する。`nextPageToken` が返った場合は cursor を更新し、次 page の `metadata_sync` を queue へ再投入する。旧 `ChannelCursor` は読み取り fallback として維持する。
- YouTube raw response 本文は S3 に保存し、DynamoDB の `Video` / `ChannelSyncCursor` には URI、件数、video id などの要約だけを保存する。
- `liveChatMessages.list` は `nextPageToken` と `pollingIntervalMillis` を記録し、Lambda 内で長時間 sleep しない。
- live chat collect は `nextPageToken` があり、`offlineAt` と `rateLimitExceeded` がない場合だけ SQS delay で再投入する。`pollingIntervalMillis` は秒へ変換し、SQS の上限に合わせて `DelaySeconds` は 900 秒で clamp する。
- `offlineAt` が返った場合は `next_poll.action=stop`、`rateLimitExceeded` の場合は `next_poll.action=retry_later` として raw chunk manifest に停止理由を残し、自動再投入しない。
- replay chat collect は公開アーカイブ HTML の `ytInitialData` から取得できる replay action と continuation を best-effort で抽出する。未知 renderer は失敗や破棄にせず `message_type=unknown` / `parse_warning=unknown_renderer` として raw JSONL に残し、manifest/result の `parser_stats` と `next_poll` に action 数、unknown 件数、continuation 件数を記録する。
- quota 使用は call record の `QuotaUsage` item に `method`、`units`、`video_count`、`channel_id`、`job_id` を top-level field として記録し、補足情報を `details` に残す。管理APIの `GET /api/admin/quota-usage` は互換用の call record `items` に加え、daily summary 由来の `daily`、`by_method`、`limit_per_day`、`warning` を返す。管理 UI の quota 表示では warning、daily summary、method summary、call records を確認できる。
- BATCH-016 `quota_rollup` は call record から `pk=QUOTA#{yyyyMMdd}` / `sk=METHOD#{method}` の daily summary を upsert し、`call_count`、`units_used`、`unit_per_call`、`source_record_count`、`warning_emitted` を保存する。日次合計が `warning_threshold_units` 以上なら `quota_threshold_warning` JobEvent を記録する。外部通知 delivery、管理 UI daily summary 表示、CloudWatch Alarm は後続対象。

## normalized chat schema

`processed/chat-normalized/video_id={video_id}/part-000.jsonl` と raw chat JSONL 内の正規化 message は `schema_version` が `chat-message/v1` の message として扱います。live/replay の入力差分を吸収し、`message_type` は `text`、`paid`、`sticker`、`unknown` のいずれかに正規化します。

必須 key は `schema_version`、`message_id`、`video_id`、`source`、`message_type`、`author`、`author_external_channel_id`、`author_name`、`author_badges`、`timestamp_usec`、`timestamp_text`、`offset_msec`、`video_offset_time_msec`、`message_runs`、`plain_text`、`message_text`、`paid`、`purchase_amount_text`、`sticker`、`raw_ref`、`raw_renderer_type`、`raw_renderer`、`parse_warning`、`collected_at` です。

unknown renderer は raw chat JSONL には `raw_renderer` として保存しますが、DynamoDB の `ChatPageManifest` には本文や renderer body を保存せず、`raw_s3_uri`、件数、hash、offset、`parser_stats` などの要約だけを残します。既存 `ChatMessageChunkManifest` は読み取り fallback として維持します。

`chat_normalize` は `ChatPageManifest.raw_s3_uri` 互換 alias の `s3_uri` から raw JSONL を line iteration で読み、normalized JSONL を出力しながら aggregate summary を更新します。集計用に全 message dict を list 化せず、`message_count`、author 数、paid 件数、emoji 件数、timeline、top terms、term timeline を streaming accumulator で生成します。

## timestamp 候補

timestamp 候補は概要欄の時刻表現、chat burst、keyword spike を統合して生成します。近接 offset の候補は `merged_sources` に由来を残して代表候補へまとめ、`evidence_terms` と `message_count` を統合します。表示順は score 降順、同点時 offset 昇順で deterministic に固定します。

## ローカル検証

```sh
npm test
npm run build
npm run package:deploy
npm run e2e:local
```

`npm run verify` で上記をまとめて実行します。

## デプロイ前成果物

`npm run package:deploy` は `build/deploy/` に次を生成します。

- `api.zip`
- `static-exporter.zip`
- `diopside.yaml`

実 AWS へのデプロイはこの作業では行いません。手動デプロイでは、rollback しやすいように release id ごとの artifact key を使います。

```sh
RELEASE_ID=$(date -u +%Y%m%d%H%M%S)

aws s3 cp build/deploy/api.zip s3://<artifact-bucket>/diopside/releases/${RELEASE_ID}/api.zip
aws s3 cp build/deploy/static-exporter.zip s3://<artifact-bucket>/diopside/releases/${RELEASE_ID}/static-exporter.zip

aws cloudformation deploy \
  --template-file build/deploy/diopside.yaml \
  --stack-name diopside-prod \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    EnvName=prod \
    AdminToken=<token> \
    AdminCsrfToken=<csrf-token> \
    YouTubeApiKey=<youtube-api-key> \
    LambdaArtifactBucket=<artifact-bucket> \
    ApiCodeS3Key=diopside/releases/${RELEASE_ID}/api.zip \
    StaticExporterCodeS3Key=diopside/releases/${RELEASE_ID}/static-exporter.zip
```

スタック作成後は Web bucket に静的 UI を同期します。public data は worker の `static_export` job で生成します。初期疎通のみ local fixture を同期する場合は、本番データ export 前の一時手順であることを明示して扱います。

```sh
npm run build
aws s3 sync build/web s3://<web-bucket>/
```

## deploy runbook

実 AWS への deploy、rollback、static export 再実行、CloudFront cache 確認は手動運用です。この repository 作業では実環境操作を実施していません。

### 初回deploy

1. local で package と test を通す。

```sh
npm run verify
```

2. `build/deploy/` の artifact を release id 付き key に upload する。

```sh
RELEASE_ID=$(date -u +%Y%m%d%H%M%S)
aws s3 cp build/deploy/api.zip s3://<artifact-bucket>/diopside/releases/${RELEASE_ID}/api.zip
aws s3 cp build/deploy/static-exporter.zip s3://<artifact-bucket>/diopside/releases/${RELEASE_ID}/static-exporter.zip
```

3. CDK synth で現 CloudFormation parity template を生成し、CloudFormation stack を作成する。`AdminToken`、`AdminCsrfToken`、`YouTubeApiKey` は template default や repository へ保存しない。

```sh
npm run cdk:synth
```

```sh
aws cloudformation deploy \
  --template-file build/cdk.out/DiopsideStack.template.json \
  --stack-name diopside-prod \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    EnvName=prod \
    AdminToken=<token> \
    AdminCsrfToken=<csrf-token> \
    YouTubeApiKey=<youtube-api-key> \
    LambdaArtifactBucket=<artifact-bucket> \
    ApiCodeS3Key=diopside/releases/${RELEASE_ID}/api.zip \
    StaticExporterCodeS3Key=diopside/releases/${RELEASE_ID}/static-exporter.zip
```

4. stack output から配信先を控える。

```sh
aws cloudformation describe-stacks \
  --stack-name diopside-prod \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontDomainName'||OutputKey=='WebBucketName'||OutputKey=='PublicDataBucketName'||OutputKey=='ApiEndpoint']"
```

5. Web bucket へ静的 UI を同期し、管理 API から `static_export` job を起動して public data を生成する。

```sh
aws s3 sync build/web s3://<web-bucket>/ --delete

curl -sS -X POST "https://<cloudfront-domain>/api/admin/jobs/static-export" \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRF-Token: <csrf-token>" \
  -H "Content-Type: application/json" \
  -d '{"scope":"all","idempotency_key":"initial-static-export"}'
```

6. `GET /api/admin/jobs/{job_id}`、post-deploy smoke、CloudFront cache 確認で完了判定する。

### 更新deploy

更新 deploy は初回 deploy と同じく `npm run verify`、release id 付き artifact upload、`npm run cdk:synth`、CloudFormation deploy、Web bucket sync、post-deploy smoke の順で行う。`ApiCodeS3Key` と `StaticExporterCodeS3Key` は新しい release id を指定し、前回の release id と stack output を作業メモに残す。

コードだけの更新でも、public JSON schema や UI asset が変わった場合は `static_export` job を再実行する。UI だけの更新では Web bucket sync と CloudFront cache 確認を行い、API/Lambda artifact の key は変更しない。

### rollback

rollback は、直前に成功していた release id の artifact key を CloudFormation に再指定する。前回の Web artifact を保存している場合は Web bucket もその内容へ戻す。保存していない場合は、対応する git tag/commit から `npm run build` し直して `aws s3 sync build/web s3://<web-bucket>/ --delete` を実行する。

```sh
ROLLBACK_RELEASE_ID=<previous-release-id>

aws cloudformation deploy \
  --template-file build/cdk.out/DiopsideStack.template.json \
  --stack-name diopside-prod \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    EnvName=prod \
    AdminToken=<token> \
    AdminCsrfToken=<csrf-token> \
    YouTubeApiKey=<youtube-api-key> \
    LambdaArtifactBucket=<artifact-bucket> \
    ApiCodeS3Key=diopside/releases/${ROLLBACK_RELEASE_ID}/api.zip \
    StaticExporterCodeS3Key=diopside/releases/${ROLLBACK_RELEASE_ID}/static-exporter.zip
```

rollback 後は `GET /api/health`、`GET /api/admin/jobs`、`latest-manifest.json`、CloudWatch Alarm、DLQ depth を確認する。schema 互換性が疑わしい rollback では `static_export` job を再実行し、versioned public data の manifest が期待する schema を指すことを確認する。

### static export再実行

public data の再生成は CloudFront 経由の管理 API で `static_export` job を起動する。`idempotency_key` は同じ作業を重複実行しないため、日付や incident id を含む値にする。

```sh
curl -sS -X POST "https://<cloudfront-domain>/api/admin/jobs/static-export" \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRF-Token: <csrf-token>" \
  -H "Content-Type: application/json" \
  -d '{"scope":"all","idempotency_key":"static-export-<yyyymmddhhmm>"}'
```

返却された `job_id` は `GET /api/admin/jobs/{job_id}` で追跡する。完了後は `https://<cloudfront-domain>/data/latest-manifest.json` を取得し、`export_version` と versioned public path が更新されたことを確認する。失敗時は `JobEvent`、CloudWatch JSON log、StaticExport DLQ、failed debug artifact を確認する。

### CloudFront cache確認

CloudFront の確認は、default route、asset、manifest、versioned public data、API の header と body を分けて見る。

```sh
curl -I "https://<cloudfront-domain>/"
curl -I "https://<cloudfront-domain>/data/latest-manifest.json"
curl -I "https://<cloudfront-domain>/data/v/<export_version>/public/index.json"
curl -I "https://<cloudfront-domain>/api/health"
```

`/api/*` は `no-store` / `no-cache` 系 header を返すこと、`/data/latest-manifest.json` は短い cache、`/data/v/*` と `/assets/*` は versioned object として長い cache であることを確認する。manifest 更新後に古い `export_version` が返り続ける場合は、CloudFront distribution、S3 object、`static_export` job の順に切り分ける。緊急時だけ対象 path を限定して invalidation する。

```sh
DISTRIBUTION_ID=$(aws cloudformation describe-stack-resource \
  --stack-name diopside-prod \
  --logical-resource-id CloudFrontDistribution \
  --query "StackResourceDetail.PhysicalResourceId" \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id ${DISTRIBUTION_ID} \
  --paths "/data/latest-manifest.json" "/index.html"
```

## post-deploy e2e

CloudFront domain を指定して smoke を実行します。

```sh
DIOPSIDE_E2E_BASE_URL=https://<cloudfront-domain> npm run e2e:local
```

PR コメントで挙げた deploy 後確認をまとめて行う場合は、次の smoke を使います。public data は一時 directory に取得され、`tools/check-public-contract.mjs` で exporter 出力と同じ契約を検証します。管理 token/CSRF を渡した場合は `static-export` job 起動、job 完了待ち、`latest-manifest.json` 更新、job 一覧、job 詳細、quota usage も確認します。

```sh
DIOPSIDE_E2E_BASE_URL=https://<cloudfront-domain> \
DIOPSIDE_ADMIN_TOKEN=<token> \
DIOPSIDE_ADMIN_CSRF_TOKEN=<csrf-token> \
npm run smoke:post-deploy
```

管理 API を確認しない場合は `DIOPSIDE_ADMIN_TOKEN` と `DIOPSIDE_ADMIN_CSRF_TOKEN` を省略できます。

確認観点:

- `/` が表示され、検索、tag filter、詳細、timestamp、wordcloud が読める。
- `/api/health`、`/api/videos`、`/api/videos/{video_id}` が CloudFront 経由で読める。
- `/data/latest-manifest.json` と versioned public JSON、wordcloud artifact が contract を満たす。
- `/assets/*`、`/data/latest-manifest.json`、`/data/v/*`、`/api/*` が CloudFront 経由で応答し、`/api/*` は no-store header を返す。
- 管理画面から passphrase で session login し、`static-export` や `metadata-sync` job を起動できる。
- `GET /api/admin/jobs` と `GET /api/admin/jobs/{job_id}` で状態と append-only event を確認できる。
- `GET /api/admin/quota-usage` が quota usage schema を返す。
