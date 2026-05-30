# DynamoDB schema v0.4 audit

## 位置づけ

`docs/design/diopside_basic_design_v0.4.md` の 5.4.4 / 5.4.5 を正本とし、現 repository 実装は移行中の実装候補として扱う。現状は single-table、`pk` / `sk`、`by_public_date`、`by_tag`、`by_work_queue`、S3 への大型データ退避方針は近いが、item type 名、key prefix、一部 read model item に差分がある。共通属性の `schema_version`、`entity_id`、`created_at`、`updated_at` は repository writer で付与する。

主要 writer は v0.4 key shape へ段階移行しているが、legacy read model、backfill、worker 分割、状態/統計 item 分離には差分ありとして残る。

## v0.4 item type 対応表

| v0.4 item_type | v0.4 key | 現 repository / README | 状態 | 備考 |
|---|---|---|---|---|
| `AppConfig` | `APP#CONFIG` / `META` | `put_app_config` が v0.4 key で保存し、旧 `CONFIG#app` は `get_app_config` fallback | 部分実装 | 既存データ backfill と API runtime の DDB 設定読み込み接続は未対応 |
| `Channel` | `CH#{channel_id}` / `META` | `put_channel` が v0.4 key で保存し、旧 `CHANNEL#...` は `get_channel` fallback | 部分実装 | 既存データ backfill と DynamoDB 旧 item scan fallback は未対応 |
| `ChannelRef` | `APP#CHANNELS` / `CH#{channel_id}` | `put_channel` が `ChannelRef` を保存し、`list_channels` / 管理 API が read model を優先利用 | 部分実装 | 既存データ backfill は未対応 |
| `ChannelSyncCursor` | `CH#{channel_id}` / `CURSOR#uploads` | `put_channel_sync_cursor` が v0.4 key で保存し、`metadata_sync` が repository method 経由で更新。旧 `ChannelCursor` / `CHANNEL#...` は `get_channel_sync_cursor` fallback | 部分実装 | 既存データ backfill と page token の hash-only 化は未対応 |
| `Video` | `VID#{video_id}` / `META` | `video_item` が v0.4 key で保存し、public GSI は `PUB#{inverted_published_at}#{video_id}`。旧 `VIDEO#...` は `get_video` fallback | 部分実装 | 既存データ backfill、legacy `VideoTagIndex` key 移行、状態/統計 item 分離は未対応 |
| `VideoMonthIndex` | `VID#{video_id}` / `INDEX#MONTH#{yyyyMM}` | `put_video` が `VideoMonthIndex` を保存し、archive calendar API / static export が read model を優先利用 | 部分実装 | 既存データ backfill は未対応 |
| `VideoStateEvent` | `VID#{video_id}` / `EVT#STATE#...` | `append_video_state_event` が v0.4 key で保存し、`live_status_scan` / `archive_finalize` が状態 event を append | 部分実装 | 既存状態 backfill、条件付き一意性、API/UI 表示は未対応 |
| `VideoStatSnapshot` | `VID#{video_id}` / `STAT#{yyyyMMddHH}` | `put_video_stat_snapshot` が v0.4 key で保存し、`put_video` が statistics 付き metadata 保存時に upsert | 部分実装 | 既存統計 backfill、API/UI 表示、高頻度抑止 scheduler は未対応 |
| `VideoTagLink` | `VID#{video_id}` / `TAG#{tag_id}` | `put_video` / `update_video_tags` が `VideoTagLink` を保存・削除し、既存 `VideoTagIndex` も互換維持 | 部分実装 | 既存データ backfill と tag search/list query の全面切替は未対応 |
| `TagSummary` | `TAG#{tag_id}` / `META` | `put_video` / `update_video_tags` が `TagSummary` を保存し、`list_tags` / API / static export が read model を優先利用 | 部分実装 | category/sort order の管理 UI 編集と既存データ backfill は未対応 |
| `ChatManifest` | `VID#{video_id}` / `CHAT#MANIFEST` | `put_chat_manifest` が v0.4 key で保存し、`chat_normalize` が repository method 経由で更新。旧 `VIDEO#...` は `get_chat_manifest` fallback | 部分実装 | 既存データ backfill、live/replay state machine 完全接続、ChatPageManifest 分離は未対応 |
| `ChatPageManifest` | `VID#{video_id}` / `CHAT#PAGE#{source}#{seq}` | `put_chat_page_manifest` が v0.4 key で保存し、`chat_collect` が repository method 経由で更新。旧 `ChatMessageChunkManifest` / `VIDEO#...` は `list_chat_chunks` fallback | 部分実装 | 既存データ backfill、TTL 運用、複数 replay continuation page 巡回は未対応 |
| `ChatAggregate` | `VID#{video_id}` / `CHAT#AGG#v1` | `put_chat_aggregate` が v0.4 key で保存し、旧 `VIDEO#...` / `CHAT#AGGREGATE` は `get_chat_aggregate` fallback | 部分実装 | 既存データ backfill、heatmap / source uri required 化、payload schema 完全固定は未対応 |
| `Artifact` | `VID#{video_id}` / `ARTIFACT#{artifact_type}#{artifact_version}` | `put_artifact` が versioned key で保存し、`artifact_version` / `content_hash` / `generated_at` を付与。旧 `VIDEO#...` item は list/get fallback | 部分実装 | 既存データ backfill と artifact payload schema の完全固定は未対応 |
| `NotificationPlan` | `VID#{video_id}` / `NOTIFY#{notification_type}` | `notification_plan` / `archive_finalize` が v0.4 key shape で保存 | 部分実装 | 外部通知 delivery と sent/skipped/failed 更新は未対応 |
| `StaticExport` | `EXPORT#public` / `VERSION#{exported_at}` | `static_export` job が manifest 生成・publish 成功後に history item を保存 | 部分実装 | 管理 API/UI 表示、既存履歴 backfill、superseded 更新は未対応 |
| `Job` | `JOB#{job_id}` / `META` | `create_job` が同 key を保存 | 部分実装 | `dedupe_key` ではなく `idempotency_key`、`latest_state` ではなく `derived_state` |
| `JobEvent` | `JOB#{job_id}` / `EVT#{seq}` | `append_job_event` が `EVT#{seq}` と `event_name` / `state_after` / `occurred_at` / `payload` を保存。`event_type` / `details` は互換 alias として保持 | 部分実装 | 既存 `EVENT#...` item の backfill、同一 job への高並列 append 時の条件付き seq 採番は未対応 |
| `Lock` | `LOCK#{lock_key}` / `META` | `acquire_lock` / `release_lock` が `owner_job_id`、`owner_request_id`、`acquired_at`、`expires_at` 付き `Lock` item を保存・解放 | 部分実装 | worker job への適用と実 AWS 条件式の統合確認は未対応 |
| `Idempotency` | `IDEMP#{dedupe_key}` / `META` | `create_job` が `Idempotency` item を保存し、Memory は `idempotency_index` が空でも item lookup で dedupe 可能。DynamoDB は現行の Job conditional put も維持 | 部分実装 | 既存 job への backfill、`Idempotency` item 単独の conditional write への切替は未対応 |
| `QuotaUsage` | `QUOTA#{yyyyMMdd}` / `METHOD#{method}` | `record_quota_usage` は `QUOTA#{yyyy-mm-dd}` / `{time}#{method}#{uuid}` の call record、`quota_rollup` は `QUOTA#{yyyyMMdd}` / `METHOD#{method}` の daily summary を保存 | 部分実装 | call record 互換は維持。quota threshold warning event は未実装 |
| `RandomBucket` | `RANDOM#DEFAULT` / `VID#{bucket_no}#{video_id}` | `put_video` が公開動画の `RandomBucket` を v0.4 key shape で保存し、random API が seed/count/tag/year 条件で参照 | 部分実装 | 専用 rebuild job と既存データ backfill は未対応 |

## 現 repository contract

現 repository は次を現在の互換 contract として持つ。

- `ITEM_TYPES` は `AppConfig`、`Channel`、`ChannelRef`、`ChannelSyncCursor`、`ChannelCursor`、`Video`、`VideoIndex`、`VideoTagIndex`、`VideoTagLink`、`VideoMonthIndex`、`TagSummary`、`ChatManifest`、`ChatPageManifest`、`ChatMessageChunkManifest`、`ChatAggregate`、`Artifact`、`NotificationPlan`、`StaticExport`、`Job`、`JobEvent`、`QuotaUsage`、`Lock`、`Idempotency`、`RandomBucket` を許可する。
- `AppConfig` は `APP#CONFIG` / `META` に保存し、`system_name`、`target_channel_ids`、`youtube_api_key_ssm_param`、collection/export flags、`default_locale`、`public_base_path` を持つ。旧 `CONFIG#app` / `META` は読み取り fallback で扱う。
- `Channel` は `CH#{channel_id}` / `META` に保存し、`channel_title`、`uploads_playlist_id`、`collect_enabled`、`default_tags` を持つ。旧 `CHANNEL#{channel_id}` / `META` は読み取り fallback で扱う。
- `ChannelSyncCursor` は `CH#{channel_id}` / `CURSOR#uploads` に保存し、`uploads_playlist_id`、`next_page_token`、`next_page_token_hash`、last seen video、raw response URI、saved count を持つ。旧 `ChannelCursor` / `CHANNEL#{channel_id}` / `CURSOR#metadata` は読み取り fallback で扱う。
- 公開 `Video` は `VID#{video_id}` / `META` に保存し、`gsi1pk=VIDEO#PUBLIC`、`gsi1sk=PUB#{inverted_published_at}#{video_id}` を持つ。旧 `VIDEO#{video_id}` / `META` は読み取り fallback で扱う。
- `VideoStateEvent` は `VID#{video_id}` / `EVT#STATE#{occurred_at}#{event_id}` に保存し、`event_name`、`from_state`、`to_state`、`source_job_id`、`payload` を持つ。
- `VideoStatSnapshot` は `VID#{video_id}` / `STAT#{yyyyMMddHH}` に保存し、`sampled_at`、`view_count`、`like_count`、`comment_count`、`concurrent_viewers`、`raw_s3_uri` を持つ。
- tag index は `VideoTagIndex` として `gsi2pk=TAG#{tag}` を持つ。管理タグ補正では `Video.tags` を更新し、削除されたタグの stale `VideoTagIndex` は消す。
- `VideoTagLink` は `VID#{video_id}` / `TAG#{tag_id}` に保存し、`tag_label`、`tag_type`、`source`、`published_at`、カード表示用の非正規化 field、`gsi2pk=TAG#{tag_id}` を持つ。tag 削除時は stale link も削除する。
- `ChatManifest` は `VID#{video_id}` / `CHAT#MANIFEST` に保存し、`live_collection_state`、`replay_collection_state`、`normalization_state`、`normalized_s3_uri`、`message_count` を持つ。旧 `VIDEO#{video_id}` / `CHAT#MANIFEST` は読み取り fallback で扱う。
- `ChatPageManifest` は `VID#{video_id}` / `CHAT#PAGE#{source}#{seq}` に保存し、`raw_s3_uri`、`item_count`、`checksum`、`job_id` を持つ。旧 `ChatMessageChunkManifest` / `VIDEO#{video_id}` / `CHAT#RAW#...` は読み取り fallback で扱う。
- `ChatAggregate` は `VID#{video_id}` / `CHAT#AGG#v1` に保存し、`aggregate_version`、`message_count`、`computed_at` を持つ。旧 `VIDEO#{video_id}` / `CHAT#AGGREGATE` は読み取り fallback で扱う。
- `Artifact` は `VID#{video_id}` / `ARTIFACT#{artifact_type}#{artifact_version}` に保存し、`artifact_version` と `content_hash` を必ず持つ。旧 `VIDEO#{video_id}` artifact は読み取り fallback で扱う。
- `Job` は `JOB#{job_id}` / `META` に保存し、一覧は `gsi3pk=JOB#ALL` を `by_work_queue` で Query する。
- `JobEvent` は `EVT#{seq}` の append-only item として保存され、現在状態は `state_after` または旧 `event_type` 互換 field の末尾 event から導出する。
- `Lock` は `LOCK#{lock_key}` / `META` に保存し、未期限切れ lock は別 owner から取得できず、同 owner または期限切れ lock は取得・更新できる。TTL は UNIX epoch seconds の `expires_at` に保存する。
- `Idempotency` は `IDEMP#{dedupe_key}` / `META` に保存し、MemoryRepository は item lookup でも job 重複起動を抑止する。DynamoRepository は現行の Job conditional put を主な重複抑止として維持する。
- `QuotaUsage` call record は `gsi3pk=QUOTA#ALL` を持ち、一覧は `by_work_queue` で Query する。daily summary は `record_type=daily_method_summary`、`pk=QUOTA#{yyyyMMdd}`、`sk=METHOD#{method}` として保存し、call record 一覧には混在させない。
- チャット本文、raw response、大きな集計・成果物本体は DynamoDB に保存せず、S3 URI / public path / summary のみを保持する。

## 後続修正方針

1. v0.4 key prefix へ移行する場合は、既存 `VIDEO#` / `CHANNEL#` item との互換 migration 方針を先に決める。
2. item type ごとの詳細 `schema_version` 命名と既存 DynamoDB data の common metadata backfill 方針を決める。
3. `ChannelRef`、`VideoMonthIndex`、`TagSummary`、`RandomBucket`、`StaticExport` は writer/query path 追加済みだが、rebuild/backfill/API表示は後続で扱う。
4. `JobEvent` は v0.4 の `EVT#{seq}` / `event_name` / `state_after` へ寄せた。後続で既存 `EVENT#...` item の backfill と高並列 append 時の条件付き seq 採番を設計する。
5. `QuotaUsage` daily summary を API / 管理 UI でどう見せるかを決め、quota threshold warning event と alarm へ接続する。
