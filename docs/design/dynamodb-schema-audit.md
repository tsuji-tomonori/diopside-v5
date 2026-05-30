# DynamoDB schema v0.4 audit

## 位置づけ

`docs/design/diopside_basic_design_v0.4.md` の 5.4.4 / 5.4.5 を正本とし、現 repository 実装は移行中の実装候補として扱う。現状は single-table、`pk` / `sk`、`by_public_date`、`by_tag`、`by_work_queue`、S3 への大型データ退避方針は近いが、item type 名、key prefix、`schema_version`、一部 read model item に差分がある。

## v0.4 item type 対応表

| v0.4 item_type | v0.4 key | 現 repository / README | 状態 | 備考 |
|---|---|---|---|---|
| `AppConfig` | `APP#CONFIG` / `META` | `ITEM_TYPES` で許可。README は `CONFIG#app` | 差分あり | key prefix と required fields が未整合 |
| `Channel` | `CH#{channel_id}` / `META` | `put_channel` は `CHANNEL#{channel_id}` / `META` | 差分あり | `collect_enabled` など v0.4 fields への移行が必要 |
| `ChannelRef` | `APP#CHANNELS` / `CH#{channel_id}` | なし | 未対応 | channel list は現状 `Channel` scan 相当 |
| `ChannelSyncCursor` | `CH#{channel_id}` / `CURSOR#uploads` | `ChannelCursor`、`CHANNEL#{channel_id}` / `CURSOR#{name}` | 差分あり | item_type 名と key prefix が異なる |
| `Video` | `VID#{video_id}` / `META` | `video_item` は `VIDEO#{video_id}` / `META` | 差分あり | `schema_version`、`created_at`、inverted public date などが未整合 |
| `VideoMonthIndex` | `VID#{video_id}` / `INDEX#MONTH#{yyyyMM}` | なし | 未対応 | archive calendar は現状 Video 走査または static data 由来 |
| `VideoStateEvent` | `VID#{video_id}` / `EVT#STATE#...` | なし | 未対応 | live/archive 状態遷移履歴は未分離 |
| `VideoStatSnapshot` | `VID#{video_id}` / `STAT#{yyyyMMddHH}` | なし | 未対応 | 統計 snapshot は Video read model に寄っている |
| `VideoTagLink` | `VID#{video_id}` / `TAG#{tag_id}` | `VideoTagIndex`、`TAG#{tag}` / `VIDEO#{video_id}` | 差分あり | tag link と tag index の向き・属性が異なる |
| `TagSummary` | `TAG#{tag_id}` / `META` | `list_tags` が Video tags から動的生成 | 未対応 | TagSummary item は未保存 |
| `ChatManifest` | `VID#{video_id}` / `CHAT#MANIFEST` | `ITEM_TYPES` で許可、現 key は `VIDEO#...` 系 | 差分あり | required state fields の contract が未固定 |
| `ChatPageManifest` | `VID#{video_id}` / `CHAT#PAGE#{source}#{seq}` | `ChatMessageChunkManifest`、`CHAT#RAW#...` | 差分あり | raw page manifest 名と key が異なる |
| `ChatAggregate` | `VID#{video_id}` / `CHAT#AGG#v1` | `put_chat_aggregate` は `VIDEO#...` / `CHAT#AGGREGATE` | 差分あり | heatmap / source uri など required fields が未整合 |
| `Artifact` | `VID#{video_id}` / `ARTIFACT#{artifact_type}#{artifact_version}` | `put_artifact` は `VIDEO#...` / `ARTIFACT#{artifact_type}` | 差分あり | artifact_version と content_hash required 化が必要 |
| `NotificationPlan` | `VID#{video_id}` / `NOTIFY#{notification_type}` | なし | 未対応 | BATCH-006 と合わせて実装が必要 |
| `StaticExport` | `EXPORT#public` / `VERSION#{exported_at}` | なし | 未対応 | static export history item は未保存 |
| `Job` | `JOB#{job_id}` / `META` | `create_job` が同 key を保存 | 部分実装 | `dedupe_key` ではなく `idempotency_key`、`latest_state` ではなく `derived_state` |
| `JobEvent` | `JOB#{job_id}` / `EVT#{seq}` | `append_job_event` は `EVENT#{time}#{uuid}` | 差分あり | seq / event_name / state_after ではなく event_type/details |
| `Lock` | `LOCK#{lock_key}` / `META` | `ITEM_TYPES` で許可 | 部分実装 | 取得/解放 helper と TTL contract は未実装 |
| `Idempotency` | `IDEMP#{dedupe_key}` / `META` | Memory は `idempotency_index`、DynamoDB は Job conditional put | 差分あり | 独立 item は未保存 |
| `QuotaUsage` | `QUOTA#{yyyyMMdd}` / `METHOD#{method}` | `record_quota_usage` は `QUOTA#{yyyy-mm-dd}` / `{time}#{method}#{uuid}` | 差分あり | call_count / units_used 集計 item ではなく call record |
| `RandomBucket` | `RANDOM#DEFAULT` / `VID#{bucket_no}#{video_id}` | なし | 未対応 | random API は現状時刻 rotate |

## 現 repository contract

現 repository は次を現在の互換 contract として持つ。

- `ITEM_TYPES` は `AppConfig`、`Channel`、`ChannelCursor`、`Video`、`VideoIndex`、`VideoTagIndex`、`ChatManifest`、`ChatMessageChunkManifest`、`ChatAggregate`、`Artifact`、`Job`、`JobEvent`、`QuotaUsage`、`Lock` を許可する。
- 公開 `Video` は `gsi1pk=VIDEO#PUBLIC` を持ち、DynamoDB adapter は `by_public_date` を Query する。
- tag index は `VideoTagIndex` として `gsi2pk=TAG#{tag}` を持つ。
- `Job` は `JOB#{job_id}` / `META` に保存し、一覧は `gsi3pk=JOB#ALL` を `by_work_queue` で Query する。
- `JobEvent` は append-only item として保存され、現在状態は保存値ではなく末尾 event から導出する。
- `QuotaUsage` は `gsi3pk=QUOTA#ALL` を持ち、一覧は `by_work_queue` で Query する。
- チャット本文、raw response、大きな集計・成果物本体は DynamoDB に保存せず、S3 URI / public path / summary のみを保持する。

## 後続修正方針

1. v0.4 key prefix へ移行する場合は、既存 `VIDEO#` / `CHANNEL#` item との互換 migration 方針を先に決める。
2. `schema_version`、`entity_id`、`created_at`、`updated_at` の共通属性を repository writer に追加する。
3. `ChannelRef`、`VideoMonthIndex`、`TagSummary`、`NotificationPlan`、`StaticExport`、`RandomBucket` を専用 writer と query path で追加する。
4. `JobEvent` は v0.4 の `EVT#{seq}` / `event_name` / `state_after` へ寄せるか、設計変更提案として現在の time-sort event 方式を明記する。
5. `QuotaUsage` は call record と daily aggregate のどちらを正本にするか決め、v0.4 の `METHOD#{method}` item との整合を取る。
