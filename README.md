# diopside v5

`diopside` は、白雪巴 YouTube 公開アーカイブを低コストに検索・閲覧し、公開チャットからワードクラウドとタイムスタンプ候補を生成する serverless アプリケーションです。設計根拠は `.workspace/diopside_basic_design_v0.4.md` です。

## 全体構成

- Public UI: `apps/web/public` を S3 + CloudFront で静的配信する。
- Public data: `apps/workers/static-exporter` が DynamoDB/S3 read model から `/data/latest-manifest.json` と `/data/v/{export_version}/public/...` を生成する。
- API: `apps/api` の Python Lambda handler が public API と Bearer token + CSRF 付き管理 API を提供する。
- Worker: `static_exporter.pipeline` が metadata sync、live status scan、chat collect、chat normalize、artifact rebuild を SQS 経由で実行する。
- Storage: DynamoDB single-table を小さな正本、S3 を raw/processed/public artifact の正本にする。
- 採用しないもの: SQL 系 DB、OpenSearch、ECS、EC2、常時起動サーバー。

## CloudFront path 設計

| Path | Origin | Cache |
|---|---|---|
| `/`, SPA route | Web S3 | immutable 相当。SPA rewrite で `/index.html` に集約 |
| `/assets/*` | Web S3 | 長 TTL |
| `/data/latest-manifest.json` | Public data S3 | 短 TTL |
| `/data/v/*` | Public data S3 | 長 TTL immutable |
| `/api/*` | Lambda Function URL | no-store/no-cache |

S3 origin は OAC と bucket policy で CloudFront 経由の `s3:GetObject` に限定します。

## DynamoDB item schema

物理 key は `pk` / `sk`、GSI は `by_public_date`、`by_tag`、`by_work_queue` です。実装は `apps/shared/src/diopside_core/repository.py` に集約しています。公開動画、job 一覧、quota usage 一覧は DynamoDB `scan` を使わず、公開動画は `by_public_date`、job/quota 一覧は `by_work_queue` の Query + pagination で取得します。

| item_type | pk | sk | 主な用途 |
|---|---|---|---|
| `AppConfig` | `CONFIG#app` | `...` | channel/default 設定 |
| `Channel` | `CHANNEL#{channel_id}` | `META` | 対象チャンネル |
| `ChannelCursor` | `CHANNEL#{channel_id}` | `CURSOR#{name}` | uploads playlist 差分位置。`page_token`、`next_page_token`、raw response URI、取得 video ids を保持 |
| `Video` | `VIDEO#{video_id}` | `META` | 公開動画 metadata。公開対象のみ `by_public_date` に投影し、YouTube raw response は URI のみ保持 |
| `VideoIndex` | `VIDEO#PUBLIC` | `{published_at}#{video_id}` | 公開日順 index 用 |
| `VideoTagIndex` | `TAG#{tag}` | `VIDEO#{video_id}` | tag 絞り込み |
| `ChatManifest` | `VIDEO#{video_id}` | `CHAT#MANIFEST` | normalized JSONL manifest |
| `ChatMessageChunkManifest` | `VIDEO#{video_id}` | `CHAT#RAW#{source}#{time}` | raw chunk manifest。`s3_uri`、`message_count`、`sha256`、offset範囲、`next_poll`のみを持ち、チャット本文は保存しない |
| `ChatAggregate` | `VIDEO#{video_id}` | `CHAT#AGGREGATE` | 集計 summary/top_terms/timeline |
| `Artifact` | `VIDEO#{video_id}` | `ARTIFACT#{type}` | wordcloud/timestamp public path |
| `Job` | `JOB#{job_id}` | `META` | job metadata と idempotency_key。`by_work_queue` に `JOB#ALL` として投影 |
| `JobEvent` | `JOB#{job_id}` | `EVENT#{time}#{uuid}` | append-only job event |
| `QuotaUsage` | `QUOTA#{yyyy-mm-dd}` | `{time}#{method}#{uuid}` | YouTube quota 記録。`by_work_queue` に `QUOTA#ALL` として投影 |
| `Lock` | `LOCK#{name}` | `META` | 二重実行制御 |

job は `idempotency_key` から安定した `job_id` を導出し、DynamoDB では `attribute_not_exists(pk)` の条件付き書き込みで同じ key の二重起動を避けます。状態は `Job` item の保存値ではなく、`JobEvent` の末尾イベントから導出します。

## S3 path 設計

- `raw/youtube/metadata/channel_id={channel_id}/playlistItems/{time}.json`: `playlistItems.list` raw response。
- `raw/youtube/metadata/channel_id={channel_id}/videos/{time}.json`: `videos.list` raw response。
- `raw/youtube/chat/...`: YouTube live/replay chat raw response。
- `processed/chat-normalized/video_id={video_id}/part-000.jsonl`: 正規化チャット。
- `processed/chat-aggregate/video_id={video_id}/summary.json`: 集計。
- `data/latest-manifest.json`: 最新 export への差し替え manifest。
- `data/v/{export_version}/public/index/videos-latest.json`: 最新一覧。
- `data/v/{export_version}/public/index/tags.json`: tag index。
- `data/v/{export_version}/public/search/videos-{year}.json`: 年別検索 index。
- `data/v/{export_version}/public/videos/{video_id}.json`: 動画詳細。
- `data/v/{export_version}/public/artifacts/wordcloud/{video_id}.svg`: SVG wordcloud。

`tools/check-public-contract.mjs` は local fixture、static exporter output、post-deploy smoke で取得した public data に対して、manifest/index/search/detail/tag の schema、versioned path、wordcloud artifact 実体、timestamp candidate field の整合性を検証します。

static export は `ChatAggregate.top_terms` がある動画だけ deterministic な SVG wordcloud を生成し、動画詳細 JSON の `chat_summary.wordcloud_url` と `artifacts.wordcloud` から同じ versioned public path を参照できるようにします。`top_terms` がない動画では fake/empty SVG を生成せず、`wordcloud_url` と `artifacts.wordcloud` は `null` にします。

S3 upload 時は `/data/v/{export_version}/public/...` の versioned data を先に upload し、最後に `/data/latest-manifest.json` を upload します。versioned data の upload 途中で失敗した場合は manifest を差し替えないため、既存の公開 export_version は維持されます。

## 環境変数

| 変数 | 用途 |
|---|---|
| `DIOPSIDE_TABLE_NAME` | DynamoDB table |
| `DIOPSIDE_PUBLIC_DATA_BUCKET` | public data S3 bucket |
| `DIOPSIDE_PUBLIC_DATA_PREFIX` | public data prefix。既定 `data` |
| `DIOPSIDE_ADMIN_TOKEN` | 管理 API Bearer token |
| `DIOPSIDE_ADMIN_CSRF_TOKEN` | 管理 API CSRF token |
| `DIOPSIDE_METADATA_QUEUE_URL` | metadata/live-status/retry/cancel queue |
| `DIOPSIDE_CHAT_QUEUE_URL` | chat collect queue |
| `DIOPSIDE_NORMALIZE_QUEUE_URL` | chat normalize queue |
| `DIOPSIDE_AGGREGATE_QUEUE_URL` | artifact rebuild queue |
| `DIOPSIDE_STATIC_EXPORT_QUEUE_URL` | static export queue |
| `YOUTUBE_API_KEY` または `DIOPSIDE_YOUTUBE_API_KEY` | YouTube Data API key |
| `DIOPSIDE_ALLOW_DRY_RUN_JOBS` | local 検証専用の dry-run job 許可 |

YouTube API key は CloudFormation の `YouTubeApiKey` NoEcho parameter から `WorkerFunction` の `DIOPSIDE_YOUTUBE_API_KEY` へ渡します。コードや template default には直書きしません。local 実行では `YOUTUBE_API_KEY` または `DIOPSIDE_YOUTUBE_API_KEY` を使えます。

## 運用 job

| API | job_type | 内容 |
|---|---|---|
| `POST /api/admin/jobs/metadata-sync` | `metadata_sync` | uploads playlist と `videos.list` による metadata 同期 |
| `POST /api/admin/jobs/live-status-scan` | `live_status_scan` | upcoming/live/archived 判定 |
| `POST /api/admin/jobs/chat-collect` | `chat_collect` | live/replay chat chunk 収集 |
| `POST /api/admin/jobs/chat-normalize` | `chat_normalize` | normalized JSONL と aggregate 生成 |
| `POST /api/admin/jobs/rebuild-artifacts` | `rebuild_artifacts` | wordcloud/timestamp 再生成 |
| `POST /api/admin/jobs/static-export` | `static_export` | public JSON/artifact export |
| `POST /api/admin/jobs/{job_id}/retry` | `retry_job` | failed/retryable job に `retry_requested` event を追加し、元 job type の queue へ再投入 |
| `POST /api/admin/jobs/{job_id}/cancel` | `cancel_job` | 未完了 job に `cancelled` event を追加。完了済み/失敗済み job は拒否 |

## quota 節約方針

- 通常巡回では `search.list` を使わず、uploads playlist の `playlistItems.list` と `videos.list` を使う。
- `metadata_sync` は明示 `page_token` がなければ `ChannelCursor.next_page_token` から再開する。`nextPageToken` が返った場合は cursor を更新し、次 page の `metadata_sync` を queue へ再投入する。
- YouTube raw response 本文は S3 に保存し、DynamoDB の `Video` / `ChannelCursor` には URI、件数、video id などの要約だけを保存する。
- `liveChatMessages.list` は `nextPageToken` と `pollingIntervalMillis` を記録し、Lambda 内で長時間 sleep しない。
- live chat collect は `nextPageToken` があり、`offlineAt` と `rateLimitExceeded` がない場合だけ SQS delay で再投入する。`pollingIntervalMillis` は秒へ変換し、SQS の上限に合わせて `DelaySeconds` は 900 秒で clamp する。
- `offlineAt` が返った場合は `next_poll.action=stop`、`rateLimitExceeded` の場合は `next_poll.action=retry_later` として raw chunk manifest に停止理由を残し、自動再投入しない。
- replay chat collect は公開アーカイブ HTML の `ytInitialData` から取得できる replay action と continuation を best-effort で抽出する。未知 renderer は失敗や破棄にせず `message_type=unknown` / `parse_warning=unknown_renderer` として raw JSONL に残し、manifest/result の `parser_stats` と `next_poll` に action 数、unknown 件数、continuation 件数を記録する。
- quota 使用は `QuotaUsage` item に `method`、`units`、`video_count`、`channel_id`、`job_id` を top-level field として記録し、補足情報を `details` に残す。管理APIの `GET /api/admin/quota-usage` と管理UIの quota 表示で確認できる。

## normalized chat schema

`processed/chat-normalized/video_id={video_id}/part-000.jsonl` と raw chat JSONL 内の正規化 message は `schema_version=chat-message/v1` として扱います。live/replay の入力差分を吸収し、`message_type` は `text`、`paid`、`sticker`、`unknown` のいずれかに正規化します。

必須 key は `message_id`、`video_id`、`source`、`message_type`、`author`、`timestamp_usec`、`timestamp_text`、`offset_msec`、`video_offset_time_msec`、`message_runs`、`plain_text`、`message_text`、`paid`、`sticker`、`raw_ref`、`raw_renderer_type`、`raw_renderer`、`parse_warning`、`collected_at` です。既存集計互換のため `author_external_channel_id`、`author_name`、`author_badges`、`purchase_amount_text` も同時に出力します。

unknown renderer は raw chat JSONL には `raw_renderer` として保存しますが、DynamoDB の `ChatMessageChunkManifest` には本文や renderer body を保存せず、`s3_uri`、件数、hash、offset、`parser_stats` などの要約だけを残します。

`chat_normalize` は `ChatMessageChunkManifest.s3_uri` の raw JSONL を line iteration で読み、normalized JSONL を出力しながら aggregate summary を更新します。集計用に全 message dict を list 化せず、`message_count`、author 数、paid 件数、emoji 件数、timeline、top terms、term timeline を streaming accumulator で生成します。

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

実 AWS へのデプロイはこの作業では行いません。手動デプロイ例:

```sh
aws s3 cp build/deploy/api.zip s3://<artifact-bucket>/diopside/api.zip
aws s3 cp build/deploy/static-exporter.zip s3://<artifact-bucket>/diopside/static-exporter.zip

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
    ApiCodeS3Key=diopside/api.zip \
    StaticExporterCodeS3Key=diopside/static-exporter.zip
```

スタック作成後は Web bucket に静的 UI を同期します。public data は worker の `static_export` job で生成します。初期疎通のみ local fixture を同期する場合は、本番データ export 前の一時手順であることを明示して扱います。

```sh
npm run build
aws s3 sync build/web s3://<web-bucket>/
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
- 管理画面から token/CSRF を入力し、`static-export` や `metadata-sync` job を起動できる。
- `GET /api/admin/jobs` と `GET /api/admin/jobs/{job_id}` で状態と append-only event を確認できる。
- `GET /api/admin/quota-usage` が quota usage schema を返す。
