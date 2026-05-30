from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Protocol

try:
    import boto3
    from boto3.dynamodb.conditions import Key
    from botocore.exceptions import ClientError
except Exception:  # pragma: no cover - available in Lambda package.
    boto3 = None
    Key = None
    ClientError = Exception


ITEM_TYPES = {
    "AppConfig",
    "Channel",
    "ChannelRef",
    "ChannelSyncCursor",
    "ChannelCursor",
    "Video",
    "VideoIndex",
    "VideoStateEvent",
    "VideoStatSnapshot",
    "VideoTagIndex",
    "VideoTagLink",
    "VideoMonthIndex",
    "TagSummary",
    "ChatManifest",
    "ChatPageManifest",
    "ChatMessageChunkManifest",
    "ChatAggregate",
    "Artifact",
    "NotificationPlan",
    "StaticExport",
    "Job",
    "JobEvent",
    "QuotaUsage",
    "Lock",
    "Idempotency",
    "RandomBucket",
}


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode('utf-8')).hexdigest()[:24]}"


def _unique_tags(tags: list[str]) -> list[str]:
    return list(dict.fromkeys(tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()))


def tag_id_for_label(label: str) -> str:
    return stable_id("tag", label)


def video_month_key(published_at: str | None) -> str | None:
    if not published_at or len(published_at) < 7:
        return None
    year = published_at[:4]
    month = published_at[5:7]
    if not (year.isdigit() and month.isdigit() and 1 <= int(month) <= 12):
        return None
    return f"{year}{month}"


def app_config_item(config: dict[str, Any]) -> dict[str, Any]:
    return {
        **{key: value for key, value in config.items() if key != "youtube_api_key"},
        "item_type": "AppConfig",
        "pk": "APP#CONFIG",
        "sk": "META",
        "system_name": config.get("system_name", "diopside"),
        "target_channel_ids": list(config.get("target_channel_ids", [])),
        "youtube_api_key_ssm_param": config.get("youtube_api_key_ssm_param", ""),
        "collection_enabled": bool(config.get("collection_enabled", True)),
        "public_export_enabled": bool(config.get("public_export_enabled", True)),
        "default_locale": config.get("default_locale", "ja-JP"),
        "public_base_path": config.get("public_base_path", "data"),
        "updated_at": now_iso(),
    }


def channel_ref_item(channel: dict[str, Any]) -> dict[str, Any]:
    channel_id = channel["channel_id"]
    collect_enabled = bool(channel.get("collect_enabled", channel.get("enabled", True)))
    channel_title = channel.get("channel_title") or channel.get("display_name") or channel_id
    priority = int(channel.get("priority", 100))
    stamp = now_iso()
    return {
        "item_type": "ChannelRef",
        "pk": "APP#CHANNELS",
        "sk": f"CH#{channel_id}",
        "channel_id": channel_id,
        "collect_enabled": collect_enabled,
        "enabled": collect_enabled,
        "priority": priority,
        "channel_title": channel_title,
        "display_name": channel.get("display_name") or channel_title,
        "uploads_playlist_id": channel.get("uploads_playlist_id"),
        "notification_enabled": bool(channel.get("notification_enabled", False)),
        "metadata_interval_minutes": channel.get("metadata_interval_minutes"),
        "live_scan_interval_minutes": channel.get("live_scan_interval_minutes"),
        "updated_at": channel.get("updated_at") or stamp,
    }


def channel_item(channel: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    channel_id = channel["channel_id"]
    stamp = now_iso()
    item = {
        **(existing or {}),
        **channel,
        "item_type": "Channel",
        "pk": f"CH#{channel_id}",
        "sk": "META",
        "channel_id": channel_id,
        "updated_at": stamp,
    }
    if "collect_enabled" not in item:
        item["collect_enabled"] = bool(item.get("enabled", True))
    if "enabled" not in item:
        item["enabled"] = bool(item.get("collect_enabled", True))
    if "channel_title" not in item:
        item["channel_title"] = item.get("display_name") or channel_id
    if "display_name" not in item:
        item["display_name"] = item.get("channel_title") or channel_id
    if "priority" not in item:
        item["priority"] = 100
    if "default_tags" not in item:
        item["default_tags"] = list(item.get("tags", []))
    if not item.get("created_at"):
        item["created_at"] = stamp
    return item


def channel_sync_cursor_item(channel_id: str, cursor: dict[str, Any]) -> dict[str, Any]:
    next_page_token = cursor.get("next_page_token")
    return {
        **cursor,
        "item_type": "ChannelSyncCursor",
        "pk": f"CH#{channel_id}",
        "sk": "CURSOR#uploads",
        "channel_id": channel_id,
        "uploads_playlist_id": cursor.get("uploads_playlist_id", ""),
        "last_seen_video_id": cursor.get("last_seen_video_id") or cursor.get("last_video_id"),
        "last_seen_published_at": cursor.get("last_seen_published_at"),
        "backfill_until": cursor.get("backfill_until"),
        "next_page_token": next_page_token,
        "next_page_token_hash": stable_id("page", next_page_token) if next_page_token else None,
        "last_success_at": cursor.get("last_success_at") or now_iso(),
        "last_error_at": cursor.get("last_error_at"),
        "last_error_code": cursor.get("last_error_code"),
        "updated_at": now_iso(),
    }


def video_item(video: dict[str, Any]) -> dict[str, Any]:
    video_id = video["video_id"]
    published_at = video.get("published_at") or video.get("scheduled_start_time") or "1970-01-01T00:00:00Z"
    tags = list(dict.fromkeys(video.get("tags", [])))
    item = {
        **video,
        "item_type": "Video",
        "pk": f"VID#{video_id}",
        "sk": "META",
        "updated_at": now_iso(),
        "tags": tags,
    }
    if item.get("public", True):
        item["gsi1pk"] = "VIDEO#PUBLIC"
        item["gsi1sk"] = f"PUB#{inverted_timestamp(published_at)}#{video_id}"
        item["published_at_sort"] = published_at
    return item


def video_month_index_item(video: dict[str, Any]) -> dict[str, Any] | None:
    published_at = video.get("published_at")
    yyyy_mm_key = video_month_key(published_at)
    if yyyy_mm_key is None:
        return None
    video_id = video["video_id"]
    return {
        "item_type": "VideoMonthIndex",
        "pk": f"VID#{video_id}",
        "sk": f"INDEX#MONTH#{yyyy_mm_key}",
        "video_id": video_id,
        "yyyy_mm": f"{yyyy_mm_key[:4]}-{yyyy_mm_key[4:]}",
        "published_at": published_at,
        "title": video.get("title", ""),
        "thumbnail_url": video.get("thumbnail_url"),
        "duration_sec": video.get("duration_sec"),
        "archive_state": video.get("archive_state") or video.get("live_state") or "archived",
        "detail_path": video.get("detail_path") or f"/api/videos/{video_id}",
        "tags": video.get("tags", []),
        "gsi1pk": f"VIDEO#MONTH#{yyyy_mm_key}",
        "gsi1sk": f"PUB#{published_at}#{video_id}",
        "updated_at": now_iso(),
    }


def inverted_timestamp(value: str | None) -> str:
    if not value:
        return "99999999999999"
    digits = "".join(ch for ch in value if ch.isdigit())[:14]
    if len(digits) < 14:
        digits = digits.ljust(14, "0")
    return "".join(str(9 - int(ch)) for ch in digits)


def video_state_event_name(to_state: str) -> str:
    return {
        "discovered": "video.discovered",
        "upcoming": "video.upcoming_detected",
        "live": "video.live_started",
        "archived": "video.archived",
        "unavailable": "video.unavailable",
    }.get(to_state, f"video.{to_state}")


def video_state_event_item(
    video_id: str,
    to_state: str,
    *,
    from_state: str | None = None,
    source_job_id: str | None = None,
    occurred_at: str | None = None,
    payload: dict[str, Any] | None = None,
    event_name: str | None = None,
) -> dict[str, Any]:
    occurred = occurred_at or now_iso()
    event = event_name or video_state_event_name(to_state)
    event_id = stable_id("vse", f"{video_id}:{occurred}:{from_state}:{to_state}:{source_job_id or ''}:{event}")
    return {
        "item_type": "VideoStateEvent",
        "pk": f"VID#{video_id}",
        "sk": f"EVT#STATE#{occurred}#{event_id}",
        "event_id": event_id,
        "video_id": video_id,
        "event_name": event,
        "from_state": from_state,
        "to_state": to_state,
        "source_job_id": source_job_id,
        "occurred_at": occurred,
        "payload": payload or {},
        "updated_at": now_iso(),
    }


def snapshot_hour_key(sampled_at: str) -> str:
    digits = "".join(ch for ch in sampled_at if ch.isdigit())
    return (digits[:10] if len(digits) >= 10 else digits.ljust(10, "0"))


def _stat_value(stats: dict[str, Any], *names: str) -> int | None:
    for name in names:
        if stats.get(name) is not None:
            try:
                return int(stats[name])
            except (TypeError, ValueError):
                return None
    return None


def video_stat_snapshot_item(video_id: str, stats: dict[str, Any]) -> dict[str, Any]:
    source_stats = stats.get("statistics") if isinstance(stats.get("statistics"), dict) else stats
    sampled_at = stats.get("sampled_at") or stats.get("updated_at") or now_iso()
    item = {
        "item_type": "VideoStatSnapshot",
        "pk": f"VID#{video_id}",
        "sk": f"STAT#{snapshot_hour_key(str(sampled_at))}",
        "video_id": video_id,
        "sampled_at": sampled_at,
        "view_count": _stat_value(source_stats, "view_count", "viewCount"),
        "like_count": _stat_value(source_stats, "like_count", "likeCount"),
        "comment_count": _stat_value(source_stats, "comment_count", "commentCount"),
        "concurrent_viewers": _stat_value(source_stats, "concurrent_viewers", "concurrentViewers"),
        "raw_s3_uri": stats.get("raw_s3_uri") or stats.get("raw_metadata_uri"),
        "updated_at": now_iso(),
    }
    return {key: value for key, value in item.items() if value is not None}


def has_video_stats(video: dict[str, Any]) -> bool:
    stats = video.get("statistics") if isinstance(video.get("statistics"), dict) else video
    return any(stats.get(name) is not None for name in ("view_count", "viewCount", "like_count", "likeCount", "comment_count", "commentCount", "concurrent_viewers", "concurrentViewers"))


def video_tag_link_item(video: dict[str, Any], tag_label: str) -> dict[str, Any]:
    video_id = video["video_id"]
    tag_id = tag_id_for_label(tag_label)
    published_at = video.get("published_at") or video.get("scheduled_start_time") or "1970-01-01T00:00:00Z"
    return {
        "item_type": "VideoTagLink",
        "pk": f"VID#{video_id}",
        "sk": f"TAG#{tag_id}",
        "video_id": video_id,
        "tag_id": tag_id,
        "tag_label": tag_label,
        "tag_type": "manual" if video.get("manual_tag_correction") else "generated",
        "source": "manual_admin" if video.get("manual_tag_correction") else "repository",
        "published_at": published_at,
        "title": video.get("title", ""),
        "thumbnail_url": video.get("thumbnail_url"),
        "duration_sec": video.get("duration_sec"),
        "gsi2pk": f"TAG#{tag_id}",
        "gsi2sk": f"PUB#{inverted_timestamp(published_at)}#{video_id}",
        "updated_at": now_iso(),
    }


def chat_aggregate_item(video_id: str, aggregate: dict[str, Any]) -> dict[str, Any]:
    computed_at = aggregate.get("computed_at") or now_iso()
    return {
        **aggregate,
        "item_type": "ChatAggregate",
        "pk": f"VID#{video_id}",
        "sk": "CHAT#AGG#v1",
        "video_id": video_id,
        "aggregate_version": aggregate.get("aggregate_version", "v1"),
        "message_count": int(aggregate.get("message_count", 0)),
        "computed_at": computed_at,
        "updated_at": now_iso(),
    }


def chat_manifest_item(video_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    normalized_s3_uri = manifest.get("normalized_s3_uri") or manifest.get("normalized_uri")
    item = {
        **manifest,
        "item_type": "ChatManifest",
        "pk": f"VID#{video_id}",
        "sk": "CHAT#MANIFEST",
        "video_id": video_id,
        "live_collection_state": manifest.get("live_collection_state", "not_started"),
        "replay_collection_state": manifest.get("replay_collection_state", "not_started"),
        "normalization_state": manifest.get("normalization_state", "succeeded" if normalized_s3_uri else "not_started"),
        "message_count": int(manifest.get("message_count", 0)),
        "updated_at": now_iso(),
    }
    if normalized_s3_uri:
        item["normalized_s3_uri"] = normalized_s3_uri
    if item.get("normalized_schema_version") is None:
        item["normalized_schema_version"] = "chat-message/v1"
    item.pop("normalized_uri", None)
    return item


def chat_page_manifest_item(video_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    source = str(manifest.get("source") or "replay")
    seq = int(manifest.get("seq", 1))
    raw_s3_uri = manifest.get("raw_s3_uri") or manifest.get("s3_uri")
    item_count = int(manifest.get("item_count", manifest.get("message_count", 0)))
    checksum = manifest.get("checksum") or manifest.get("sha256") or ""
    item = {
        **manifest,
        "item_type": "ChatPageManifest",
        "pk": f"VID#{video_id}",
        "sk": f"CHAT#PAGE#{source}#{seq}",
        "video_id": video_id,
        "source": source,
        "seq": seq,
        "raw_s3_uri": raw_s3_uri,
        "item_count": item_count,
        "checksum": checksum,
        "job_id": manifest.get("job_id") or f"chat_collect#{video_id}",
        "updated_at": now_iso(),
        "s3_uri": raw_s3_uri,
        "message_count": item_count,
        "sha256": checksum,
    }
    return item


def _next_seq(items: list[dict[str, Any]]) -> int:
    seqs = [int(item.get("seq", 0)) for item in items if str(item.get("seq", "")).isdigit()]
    return (max(seqs) if seqs else len(items)) + 1


def random_bucket_item(video: dict[str, Any]) -> dict[str, Any]:
    video_id = video["video_id"]
    bucket_no = int(hashlib.sha256(video_id.encode("utf-8")).hexdigest()[:8], 16) % 10000
    return {
        "item_type": "RandomBucket",
        "pk": "RANDOM#DEFAULT",
        "sk": f"VID#{bucket_no:04d}#{video_id}",
        "bucket_no": bucket_no,
        "video_id": video_id,
        "title": video.get("title", ""),
        "thumbnail_url": video.get("thumbnail_url"),
        "duration_sec": video.get("duration_sec"),
        "published_at": video.get("published_at"),
        "tags": video.get("tags", []),
        "generated_at": now_iso(),
    }


def artifact_content_hash(artifact: dict[str, Any]) -> str:
    if artifact.get("content_hash"):
        return str(artifact["content_hash"])
    source = {
        key: value
        for key, value in artifact.items()
        if key not in {"created_at", "updated_at", "generated_at", "content_hash"}
    }
    body = json.dumps(source, ensure_ascii=False, sort_keys=True, default=str)
    return f"sha256:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"


def artifact_item(video_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
    artifact_type = artifact["artifact_type"]
    artifact_version = str(artifact.get("artifact_version") or "v1")
    generated_at = artifact.get("generated_at") or now_iso()
    item = {
        **artifact,
        "item_type": "Artifact",
        "pk": f"VID#{video_id}",
        "sk": f"ARTIFACT#{artifact_type}#{artifact_version}",
        "video_id": video_id,
        "artifact_id": artifact.get("artifact_id") or f"{video_id}:{artifact_type}",
        "artifact_type": artifact_type,
        "artifact_version": artifact_version,
        "generated_at": generated_at,
        "updated_at": now_iso(),
    }
    item["content_hash"] = artifact_content_hash(item)
    return item


def static_export_item(
    manifest: dict[str, Any],
    *,
    reason: str = "manual",
    manifest_s3_uri: str | None = None,
    public_prefix: str | None = None,
    video_count: int | None = None,
    tag_count: int | None = None,
    generated_job_id: str | None = None,
    uploaded_object_count: int | None = None,
    publish_state: str = "published",
) -> dict[str, Any]:
    exported_at = manifest["generated_at"]
    export_version = manifest["export_version"]
    static_paths = manifest.get("static_paths", {})
    content_hash = static_paths.get("STATIC-006", {}).get("checksum_sha256") or hashlib.sha256(
        repr(manifest).encode("utf-8")
    ).hexdigest()
    item = {
        "item_type": "StaticExport",
        "pk": "EXPORT#public",
        "sk": f"VERSION#{exported_at}",
        "export_id": stable_id("export", export_version),
        "export_version": export_version,
        "exported_at": exported_at,
        "reason": reason,
        "manifest_s3_uri": manifest_s3_uri or "local://latest-manifest.json",
        "public_prefix": public_prefix or f"data/v/{export_version}/public",
        "video_count": video_count if video_count is not None else len(static_paths.get("STATIC-003", {}).get("items", {})),
        "tag_count": tag_count if tag_count is not None else int(manifest.get("tag_count", 0)),
        "schema_versions": _static_export_schema_versions(manifest),
        "content_hash": content_hash,
        "publish_state": publish_state,
        "updated_at": now_iso(),
    }
    if generated_job_id:
        item["generated_job_id"] = generated_job_id
    if uploaded_object_count is not None:
        item["uploaded_object_count"] = uploaded_object_count
    return item


def _static_export_schema_versions(manifest: dict[str, Any]) -> dict[str, str]:
    versions = {"manifest": manifest.get("schema_version", "public-manifest/v1")}
    versions.update(
        {
            "home": "public-home/v1",
            "video_list": "public-video-list/v1",
            "tag_list": "public-tag-list/v1",
            "video_search": "public-video-search/v1",
            "archive_calendar": "public-archive-calendar/v1",
            "video_detail": "public-video-detail/v1",
            "wordcloud": "public-wordcloud/v1",
            "timestamps": "public-timestamp-list/v1",
        }
    )
    return versions


def request_hash(job_type: str, payload: dict[str, Any]) -> str:
    body = json.dumps({"job_type": job_type, "payload": payload}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def idempotency_item(idempotency_key: str, job_id: str, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_type": "Idempotency",
        "pk": f"IDEMP#{idempotency_key}",
        "sk": "META",
        "dedupe_key": idempotency_key,
        "idempotency_key": idempotency_key,
        "entity_id": idempotency_key,
        "first_job_id": job_id,
        "job_id": job_id,
        "job_type": job_type,
        "request_hash": request_hash(job_type, payload),
    }


def lock_item(lock_key: str, owner_job_id: str, ttl_seconds: int, owner_request_id: str | None = None) -> dict[str, Any]:
    now = int(time.time())
    stamp = now_iso()
    item = {
        "item_type": "Lock",
        "pk": f"LOCK#{lock_key}",
        "sk": "META",
        "lock_key": lock_key,
        "owner_job_id": owner_job_id,
        "acquired_at": stamp,
        "expires_at": now + ttl_seconds,
    }
    if owner_request_id:
        item["owner_request_id"] = owner_request_id
    return item


def item_schema_version(item_type: str) -> str:
    return f"ddb-{item_type}-v1"


def item_entity_id(item: dict[str, Any]) -> str:
    for key in [
        "entity_id",
        "video_id",
        "channel_id",
        "tag_id",
        "job_id",
        "export_id",
        "artifact_id",
        "lock_key",
        "quota_date",
        "idempotency_key",
    ]:
        value = item.get(key)
        if value:
            return str(value)
    return f"{item['pk']}#{item['sk']}"


def normalize_item_metadata(item: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = deepcopy(item)
    stamp = now_iso()
    if not normalized.get("schema_version"):
        normalized["schema_version"] = existing.get("schema_version") if existing else item_schema_version(normalized["item_type"])
    if not normalized.get("entity_id"):
        normalized["entity_id"] = existing.get("entity_id") if existing else item_entity_id(normalized)
    if not normalized.get("created_at"):
        normalized["created_at"] = existing.get("created_at") if existing else normalized.get("updated_at", stamp)
    if not normalized.get("updated_at"):
        normalized["updated_at"] = stamp
    return normalized


JOB_STATE_BY_EVENT_TYPE = {
    "queued": "queued",
    "started": "running",
    "completed": "succeeded",
    "succeeded": "succeeded",
    "failed": "failed",
    "retry_requested": "retryable",
    "retry_scheduled": "retryable",
    "cancelled": "cancelled",
    "canceled": "cancelled",
}

JOB_LIST_STATES = ("queued", "running", "retryable", "succeeded", "failed", "cancelled", "canceled")


def job_event_name(event_type: str) -> str:
    if "." in event_type:
        return event_type
    aliases = {
        "completed": "succeeded",
        "cancelled": "canceled",
    }
    return f"job.{aliases.get(event_type, event_type)}"


def job_state_after(event_type: str) -> str:
    short_name = event_type.rsplit(".", 1)[-1]
    return JOB_STATE_BY_EVENT_TYPE.get(short_name, short_name)


def job_event_sort_key(item: dict[str, Any]) -> tuple[str, int, str]:
    occurred_at = item.get("occurred_at") or item.get("created_at", "")
    seq = item.get("seq")
    if isinstance(seq, int):
        return (occurred_at, seq, item.get("sk", ""))
    sk = item.get("sk", "")
    if sk.startswith("EVT#"):
        try:
            return (occurred_at, int(sk.removeprefix("EVT#")), sk)
        except ValueError:
            pass
    return (occurred_at, 0, sk)


def next_job_event_seq(events: list[dict[str, Any]]) -> int:
    seqs: list[int] = []
    for item in events:
        seq = item.get("seq")
        if isinstance(seq, int):
            seqs.append(seq)
            continue
        sk = item.get("sk", "")
        if sk.startswith("EVT#"):
            try:
                seqs.append(int(sk.removeprefix("EVT#")))
            except ValueError:
                continue
    return (max(seqs) + 1) if seqs else 1


def job_event_item(job_id: str, event_type: str, details: dict[str, Any] | None, seq: int) -> dict[str, Any]:
    stamp = now_iso()
    payload = details or {}
    state_after = job_state_after(event_type)
    return {
        "item_type": "JobEvent",
        "pk": f"JOB#{job_id}",
        "sk": f"EVT#{seq:08d}",
        "job_id": job_id,
        "seq": seq,
        "event_name": job_event_name(event_type),
        "state_after": state_after,
        "occurred_at": stamp,
        "payload": payload,
        "event_type": event_type,
        "details": payload,
        "created_at": stamp,
    }


def derive_job_state(events: list[dict[str, Any]]) -> str:
    if not events:
        return "queued"
    latest = sorted(events, key=job_event_sort_key)[-1]
    state_after = latest.get("state_after")
    if state_after:
        return str(state_after)
    return job_state_after(str(latest.get("event_type") or latest.get("event_name") or "queued"))


def normalize_job_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in events:
        event = deepcopy(item)
        event_type = str(event.get("event_type") or event.get("event_name", "").rsplit(".", 1)[-1] or "queued")
        if "event_name" not in event:
            event["event_name"] = job_event_name(event_type)
        if "state_after" not in event:
            event["state_after"] = job_state_after(event_type)
        if "payload" not in event:
            event["payload"] = deepcopy(event.get("details", {}))
        if "details" not in event:
            event["details"] = deepcopy(event.get("payload", {}))
        if "event_type" not in event:
            event["event_type"] = event_type
        if "occurred_at" not in event:
            event["occurred_at"] = event.get("created_at")
        normalized.append(event)
    normalized.sort(key=job_event_sort_key)
    return normalized


def job_events_for_job(items: list[dict[str, Any]], job_id: str) -> list[dict[str, Any]]:
    return [item for item in items if item.get("pk") == f"JOB#{job_id}" and item.get("item_type") == "JobEvent"]


def job_target(payload: dict[str, Any], job_type: str) -> tuple[str, str | None]:
    if payload.get("video_id"):
        return "video", str(payload["video_id"])
    if payload.get("channel_id"):
        return "channel", str(payload["channel_id"])
    if payload.get("uploads_playlist_id"):
        return "channel", str(payload["uploads_playlist_id"])
    if job_type == "static_export" or payload.get("scope"):
        return "export", str(payload.get("scope") or "public")
    return "system", None


def update_job_read_model(job: dict[str, Any], latest_state: str, *, next_run_at: str | None = None) -> dict[str, Any]:
    updated = deepcopy(job)
    run_at = next_run_at or updated.get("next_run_at") or updated.get("queued_at") or updated.get("created_at") or now_iso()
    updated["latest_state"] = latest_state
    updated["derived_state"] = latest_state
    updated["next_run_at"] = run_at
    updated["gsi3pk"] = f"JOB#STATE#{latest_state}"
    updated["gsi3sk"] = f"NEXT#{run_at}#{updated['job_id']}"
    updated["updated_at"] = now_iso()
    return updated


class Repository(Protocol):
    def put_item(self, item: dict[str, Any]) -> dict[str, Any]: ...
    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None: ...
    def delete_item(self, pk: str, sk: str) -> None: ...
    def list_videos(self, limit: int = 100) -> list[dict[str, Any]]: ...
    def get_video(self, video_id: str) -> dict[str, Any] | None: ...
    def list_video_month_indexes(self, year: int | None = None, month: int | None = None) -> list[dict[str, Any]]: ...
    def list_tags(self) -> list[dict[str, Any]]: ...
    def rebuild_tag_summaries(self, tags: list[str] | None = None) -> list[dict[str, Any]]: ...
    def list_random_videos(self, limit: int = 1000) -> list[dict[str, Any]]: ...
    def record_static_export(self, manifest: dict[str, Any], **kwargs: Any) -> dict[str, Any]: ...
    def list_static_exports(self, limit: int = 20) -> list[dict[str, Any]]: ...
    def put_video(self, video: dict[str, Any]) -> dict[str, Any]: ...
    def get_channel(self, channel_id: str) -> dict[str, Any] | None: ...
    def append_video_state_event(self, video_id: str, to_state: str, *, from_state: str | None = None, source_job_id: str | None = None, payload: dict[str, Any] | None = None, occurred_at: str | None = None, event_name: str | None = None) -> dict[str, Any]: ...
    def put_video_stat_snapshot(self, video_id: str, stats: dict[str, Any]) -> dict[str, Any]: ...
    def update_video_tags(self, video_id: str, *, add_tags: list[str] | None = None, remove_tags: list[str] | None = None, replace_tags: list[str] | None = None) -> dict[str, Any]: ...
    def put_app_config(self, config: dict[str, Any]) -> dict[str, Any]: ...
    def get_app_config(self) -> dict[str, Any] | None: ...
    def put_channel_sync_cursor(self, channel_id: str, cursor: dict[str, Any]) -> dict[str, Any]: ...
    def get_channel_sync_cursor(self, channel_id: str) -> dict[str, Any] | None: ...
    def put_chat_aggregate(self, video_id: str, aggregate: dict[str, Any]) -> dict[str, Any]: ...
    def get_chat_aggregate(self, video_id: str) -> dict[str, Any] | None: ...
    def put_chat_manifest(self, video_id: str, manifest: dict[str, Any]) -> dict[str, Any]: ...
    def get_chat_manifest(self, video_id: str) -> dict[str, Any] | None: ...
    def put_chat_page_manifest(self, video_id: str, manifest: dict[str, Any]) -> dict[str, Any]: ...
    def put_artifact(self, video_id: str, artifact: dict[str, Any]) -> dict[str, Any]: ...
    def list_artifacts(self, video_id: str) -> list[dict[str, Any]]: ...
    def get_artifact_by_id(self, artifact_id: str) -> dict[str, Any] | None: ...
    def put_channel(self, channel: dict[str, Any]) -> dict[str, Any]: ...
    def record_quota_usage(
        self,
        method: str,
        units: int,
        details: dict[str, Any] | None = None,
        *,
        channel_id: str | None = None,
        video_count: int | None = None,
        job_id: str | None = None,
    ) -> dict[str, Any]: ...
    def create_job(self, job_type: str, payload: dict[str, Any], idempotency_key: str) -> tuple[dict[str, Any], bool]: ...
    def get_job(self, job_id: str) -> dict[str, Any] | None: ...
    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]: ...
    def append_job_event(self, job_id: str, event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]: ...
    def acquire_lock(self, lock_key: str, owner_job_id: str, ttl_seconds: int = 900, owner_request_id: str | None = None) -> dict[str, Any] | None: ...
    def release_lock(self, lock_key: str, owner_job_id: str) -> bool: ...
    def list_chat_chunks(self, video_id: str) -> list[dict[str, Any]]: ...
    def list_channels(self) -> list[dict[str, Any]]: ...
    def list_quota_usage(self, limit: int = 100) -> list[dict[str, Any]]: ...


@dataclass
class MemoryRepository:
    items: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    idempotency_index: dict[str, str] = field(default_factory=dict)

    def put_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if item.get("item_type") not in ITEM_TYPES:
            raise ValueError(f"unsupported item_type: {item.get('item_type')}")
        normalized = normalize_item_metadata(item, self.items.get((item["pk"], item["sk"])))
        self.items[(normalized["pk"], normalized["sk"])] = deepcopy(normalized)
        return deepcopy(normalized)

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None:
        item = self.items.get((pk, sk))
        return deepcopy(item) if item else None

    def delete_item(self, pk: str, sk: str) -> None:
        self.items.pop((pk, sk), None)

    def list_videos(self, limit: int = 100) -> list[dict[str, Any]]:
        videos = [item for item in self.items.values() if item.get("item_type") == "Video" and item.get("public", True)]
        videos.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        return deepcopy(videos[:limit])

    def get_video(self, video_id: str) -> dict[str, Any] | None:
        return self.get_item(f"VID#{video_id}", "META") or self.get_item(f"VIDEO#{video_id}", "META")

    def list_video_month_indexes(self, year: int | None = None, month: int | None = None) -> list[dict[str, Any]]:
        indexes = [item for item in self.items.values() if item.get("item_type") == "VideoMonthIndex"]
        if not indexes:
            indexes = [item for video in self.list_videos(10000) if (item := video_month_index_item(video))]
        if year is not None:
            indexes = [item for item in indexes if item.get("yyyy_mm", "").startswith(f"{year:04d}-")]
        if month is not None:
            indexes = [item for item in indexes if item.get("yyyy_mm", "").endswith(f"-{month:02d}")]
        indexes.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        return deepcopy(indexes)

    def list_tags(self) -> list[dict[str, Any]]:
        summaries = [item for item in self.items.values() if item.get("item_type") == "TagSummary"]
        if summaries:
            summaries = [item for item in summaries if item.get("public_visible", True)]
            summaries.sort(key=lambda item: (int(item.get("sort_order", 0)), item.get("label", "")))
            return [
                {
                    "tag_id": item["tag_id"],
                    "label": item["label"],
                    "video_count": int(item.get("video_count", 0)),
                    "category": item.get("category", "auto"),
                    "aliases": item.get("aliases", []),
                    "latest_video_id": item.get("latest_video_id"),
                    "latest_video_at": item.get("latest_video_at"),
                    "sort_order": int(item.get("sort_order", 0)),
                    "public_visible": bool(item.get("public_visible", True)),
                }
                for item in summaries
            ]
        return self._dynamic_tag_summaries()

    def _dynamic_tag_summaries(self) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for video in self.list_videos(10000):
            for tag in video.get("tags", []):
                counts[tag] = counts.get(tag, 0) + 1
        return [
            {
                "tag_id": tag_id_for_label(tag),
                "label": tag,
                "video_count": count,
                "category": "auto",
                "aliases": [],
                "public_visible": True,
                "sort_order": 0,
            }
            for tag, count in sorted(counts.items())
        ]

    def rebuild_tag_summaries(self, tags: list[str] | None = None) -> list[dict[str, Any]]:
        target_tags = set(_unique_tags(tags or []))
        if not target_tags:
            target_tags = {tag for video in self.list_videos(10000) for tag in video.get("tags", [])}
        summaries = []
        for tag in sorted(target_tags):
            videos = [video for video in self.list_videos(10000) if tag in video.get("tags", [])]
            videos.sort(key=lambda item: item.get("published_at", ""), reverse=True)
            existing = self.get_item(f"TAG#{tag_id_for_label(tag)}", "META") or {}
            latest = videos[0] if videos else {}
            item = {
                **existing,
                "item_type": "TagSummary",
                "pk": f"TAG#{tag_id_for_label(tag)}",
                "sk": "META",
                "tag_id": tag_id_for_label(tag),
                "label": existing.get("label", tag),
                "category": existing.get("category", "auto"),
                "aliases": existing.get("aliases", []),
                "video_count": len(videos),
                "latest_video_id": latest.get("video_id"),
                "latest_video_at": latest.get("published_at"),
                "sort_order": int(existing.get("sort_order", 0)),
                "public_visible": len(videos) > 0 and bool(existing.get("public_visible", True)),
                "gsi2pk": "TAG#SUMMARY",
                "gsi2sk": f"{int(existing.get('sort_order', 0)):08d}#{tag}",
                "updated_at": now_iso(),
            }
            summaries.append(self.put_item(item))
        return summaries

    def put_video(self, video: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_video(video["video_id"])
        previous_tags = set(existing.get("tags", [])) if existing else set()
        previous_month_key = video_month_key(existing.get("published_at")) if existing else None
        item = self.put_item(video_item({**(existing or {}), **video}))
        current_month_index = video_month_index_item(item)
        current_month_key = current_month_index["sk"].replace("INDEX#MONTH#", "") if current_month_index else None
        if previous_month_key and previous_month_key != current_month_key:
            self.delete_item(f"VID#{item['video_id']}", f"INDEX#MONTH#{previous_month_key}")
        if item.get("public", True) and current_month_index:
            self.put_item(current_month_index)
        elif current_month_key:
            self.delete_item(f"VID#{item['video_id']}", f"INDEX#MONTH#{current_month_key}")
        current_tags = set(item.get("tags", []))
        for tag in previous_tags - current_tags:
            self.delete_item(f"TAG#{tag}", f"VIDEO#{item['video_id']}")
            self.delete_item(f"VID#{item['video_id']}", f"TAG#{tag_id_for_label(tag)}")
        for tag in item.get("tags", []):
            self.put_item(
                {
                    "item_type": "VideoTagIndex",
                    "pk": f"TAG#{tag}",
                    "sk": f"VIDEO#{item['video_id']}",
                    "video_id": item["video_id"],
                    "tag": tag,
                    "gsi2pk": f"TAG#{tag}",
                    "gsi2sk": item.get("published_at", ""),
                    "updated_at": now_iso(),
                }
            )
            self.put_item(video_tag_link_item(item, tag))
        random_bucket = random_bucket_item(item)
        if item.get("public", True):
            self.put_item(random_bucket)
        else:
            self.delete_item(random_bucket["pk"], random_bucket["sk"])
        if has_video_stats(item):
            self.put_video_stat_snapshot(item["video_id"], item)
        self.rebuild_tag_summaries(sorted(previous_tags | current_tags))
        return item

    def append_video_state_event(self, video_id: str, to_state: str, *, from_state: str | None = None, source_job_id: str | None = None, payload: dict[str, Any] | None = None, occurred_at: str | None = None, event_name: str | None = None) -> dict[str, Any]:
        return self.put_item(
            video_state_event_item(
                video_id,
                to_state,
                from_state=from_state,
                source_job_id=source_job_id,
                payload=payload,
                occurred_at=occurred_at,
                event_name=event_name,
            )
        )

    def put_video_stat_snapshot(self, video_id: str, stats: dict[str, Any]) -> dict[str, Any]:
        return self.put_item(video_stat_snapshot_item(video_id, stats))

    def list_random_videos(self, limit: int = 1000) -> list[dict[str, Any]]:
        items = [item for (pk, sk), item in self.items.items() if pk == "RANDOM#DEFAULT" and sk.startswith("VID#") and item.get("item_type") == "RandomBucket"]
        items.sort(key=lambda item: item.get("sk", ""))
        return deepcopy(items[:limit])

    def record_static_export(self, manifest: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        item = static_export_item(manifest, **kwargs)
        return self.put_item(item)

    def list_static_exports(self, limit: int = 20) -> list[dict[str, Any]]:
        exports = [item for (pk, sk), item in self.items.items() if pk == "EXPORT#public" and sk.startswith("VERSION#") and item.get("item_type") == "StaticExport"]
        exports.sort(key=lambda item: item.get("exported_at", ""), reverse=True)
        return deepcopy(exports[:limit])

    def update_video_tags(self, video_id: str, *, add_tags: list[str] | None = None, remove_tags: list[str] | None = None, replace_tags: list[str] | None = None) -> dict[str, Any]:
        video = self.get_video(video_id)
        if not video:
            raise KeyError(video_id)
        if replace_tags is not None:
            tags = _unique_tags(replace_tags)
        else:
            remove = set(remove_tags or [])
            tags = [tag for tag in video.get("tags", []) if tag not in remove]
            tags.extend(add_tags or [])
            tags = _unique_tags(tags)
        stamp = now_iso()
        manual = {
            "add_tags": _unique_tags(add_tags or []),
            "remove_tags": _unique_tags(remove_tags or []),
            **({"replace_tags": _unique_tags(replace_tags)} if replace_tags is not None else {}),
            "updated_at": stamp,
        }
        return self.put_video({**video, "tags": tags, "manual_tag_correction": manual, "manual_tags_updated_at": stamp})

    def put_chat_aggregate(self, video_id: str, aggregate: dict[str, Any]) -> dict[str, Any]:
        return self.put_item(chat_aggregate_item(video_id, aggregate))

    def get_chat_aggregate(self, video_id: str) -> dict[str, Any] | None:
        return self.get_item(f"VID#{video_id}", "CHAT#AGG#v1") or self.get_item(f"VIDEO#{video_id}", "CHAT#AGGREGATE")

    def put_chat_manifest(self, video_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        return self.put_item(chat_manifest_item(video_id, manifest))

    def get_chat_manifest(self, video_id: str) -> dict[str, Any] | None:
        return self.get_item(f"VID#{video_id}", "CHAT#MANIFEST") or self.get_item(f"VIDEO#{video_id}", "CHAT#MANIFEST")

    def put_chat_page_manifest(self, video_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        source = str(manifest.get("source") or "replay")
        if manifest.get("seq") is None:
            existing = [item for item in self.list_chat_chunks(video_id) if item.get("source") == source]
            manifest = {**manifest, "seq": _next_seq(existing)}
        return self.put_item(chat_page_manifest_item(video_id, manifest))

    def put_artifact(self, video_id: str, artifact: dict[str, Any]) -> dict[str, Any]:
        return self.put_item(artifact_item(video_id, artifact))

    def list_artifacts(self, video_id: str) -> list[dict[str, Any]]:
        prefixes = [f"VID#{video_id}", f"VIDEO#{video_id}"]
        artifacts = [
            item
            for (pk, sk), item in self.items.items()
            if pk in prefixes and sk.startswith("ARTIFACT#") and item.get("item_type") == "Artifact"
        ]
        artifacts.sort(key=lambda item: (item.get("artifact_type", ""), item.get("artifact_version", ""), item.get("generated_at", "")))
        return deepcopy(artifacts)

    def record_quota_usage(
        self,
        method: str,
        units: int,
        details: dict[str, Any] | None = None,
        *,
        channel_id: str | None = None,
        video_count: int | None = None,
        job_id: str | None = None,
    ) -> dict[str, Any]:
        stamp = now_iso()
        usage_details = details or {}
        normalized_channel_id = channel_id if channel_id is not None else usage_details.get("channel_id")
        normalized_video_count = video_count if video_count is not None else usage_details.get("video_count")
        normalized_job_id = job_id if job_id is not None else usage_details.get("job_id")
        return self.put_item(
            {
                "item_type": "QuotaUsage",
                "pk": f"QUOTA#{stamp[:10]}",
                "sk": f"{stamp}#{method}#{uuid.uuid4().hex}",
                "method": method,
                "units": units,
                "channel_id": normalized_channel_id,
                "video_count": normalized_video_count,
                "job_id": normalized_job_id,
                "details": {**usage_details, "channel_id": normalized_channel_id, "video_count": normalized_video_count, "job_id": normalized_job_id},
                "record_type": "call",
                "created_at": stamp,
                "gsi3pk": "QUOTA#ALL",
                "gsi3sk": f"{stamp}#{method}",
            }
        )

    def create_job(self, job_type: str, payload: dict[str, Any], idempotency_key: str) -> tuple[dict[str, Any], bool]:
        if idempotency_key in self.idempotency_index:
            existing = self.get_job(self.idempotency_index[idempotency_key])
            if existing:
                return existing, True
        idempotency = self.get_item(f"IDEMP#{idempotency_key}", "META")
        if idempotency:
            existing = self.get_job(str(idempotency.get("first_job_id") or idempotency.get("job_id")))
            if existing:
                self.idempotency_index[idempotency_key] = existing["job_id"]
                return existing, True
        stamp = now_iso()
        job_id = stable_id("job", idempotency_key)
        target_type, target_id = job_target(payload, job_type)
        item = {
            "item_type": "Job",
            "pk": f"JOB#{job_id}",
            "sk": "META",
            "job_id": job_id,
            "job_type": job_type,
            "target_type": target_type,
            "target_id": target_id,
            "dedupe_key": idempotency_key,
            "idempotency_key": idempotency_key,
            "input": payload,
            "payload": payload,
            "latest_state": "queued",
            "derived_state": "queued",
            "attempt": 0,
            "max_attempts": int(payload.get("max_attempts") or 3),
            "queued_at": stamp,
            "next_run_at": payload.get("next_run_at") or stamp,
            "created_at": stamp,
            "updated_at": stamp,
            "gsi3pk": "JOB#STATE#queued",
            "gsi3sk": f"NEXT#{payload.get('next_run_at') or stamp}#{job_id}",
        }
        self.put_item(item)
        self.put_item(idempotency_item(idempotency_key, job_id, job_type, payload))
        self.idempotency_index[idempotency_key] = job_id
        self.append_job_event(job_id, "queued", {"job_type": job_type})
        return self.get_job(job_id) or item, False

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.get_item(f"JOB#{job_id}", "META")
        if not job:
            return None
        events = normalize_job_events(job_events_for_job(list(self.items.values()), job_id))
        job["events"] = deepcopy(events)
        latest_state = derive_job_state(events)
        job["latest_state"] = latest_state
        job["derived_state"] = latest_state
        return job

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        jobs = [self.get_job(item["job_id"]) for item in self.items.values() if item.get("item_type") == "Job"]
        present = [job for job in jobs if job]
        present.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return deepcopy(present[:limit])

    def append_job_event(self, job_id: str, event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        events = job_events_for_job(list(self.items.values()), job_id)
        event = self.put_item(job_event_item(job_id, event_type, details, next_job_event_seq(events)))
        job = self.get_item(f"JOB#{job_id}", "META")
        if job:
            updated_events = normalize_job_events([*events, event])
            self.put_item(update_job_read_model(job, derive_job_state(updated_events)))
        return event

    def put_app_config(self, config: dict[str, Any]) -> dict[str, Any]:
        return self.put_item(app_config_item(config))

    def get_app_config(self) -> dict[str, Any] | None:
        return self.get_item("APP#CONFIG", "META") or self.get_item("CONFIG#app", "META")

    def put_channel_sync_cursor(self, channel_id: str, cursor: dict[str, Any]) -> dict[str, Any]:
        return self.put_item(channel_sync_cursor_item(channel_id, cursor))

    def get_channel_sync_cursor(self, channel_id: str) -> dict[str, Any] | None:
        return self.get_item(f"CH#{channel_id}", "CURSOR#uploads") or self.get_item(f"CHANNEL#{channel_id}", "CURSOR#metadata")

    def acquire_lock(self, lock_key: str, owner_job_id: str, ttl_seconds: int = 900, owner_request_id: str | None = None) -> dict[str, Any] | None:
        existing = self.get_item(f"LOCK#{lock_key}", "META")
        now = int(time.time())
        if existing and int(existing.get("expires_at", 0)) > now and existing.get("owner_job_id") != owner_job_id:
            return None
        return self.put_item(lock_item(lock_key, owner_job_id, ttl_seconds, owner_request_id))

    def release_lock(self, lock_key: str, owner_job_id: str) -> bool:
        existing = self.get_item(f"LOCK#{lock_key}", "META")
        if not existing or existing.get("owner_job_id") != owner_job_id:
            return False
        self.delete_item(f"LOCK#{lock_key}", "META")
        return True

    def list_chat_chunks(self, video_id: str) -> list[dict[str, Any]]:
        chunks = [item for (pk, _), item in self.items.items() if pk == f"VID#{video_id}" and item.get("item_type") == "ChatPageManifest"]
        if not chunks:
            chunks = [item for (pk, _), item in self.items.items() if pk == f"VIDEO#{video_id}" and item.get("item_type") == "ChatMessageChunkManifest"]
        chunks.sort(key=lambda item: (int(item.get("seq", 0)), item.get("sk", "")))
        return deepcopy(chunks)

    def list_channels(self) -> list[dict[str, Any]]:
        refs = [item for item in self.items.values() if item.get("item_type") == "ChannelRef"]
        if refs:
            refs.sort(key=lambda item: (int(item.get("priority", 100)), item.get("channel_id", "")))
            return deepcopy(refs)
        channels = [item for item in self.items.values() if item.get("item_type") == "Channel"]
        channels.sort(key=lambda item: item.get("channel_id", ""))
        return deepcopy(channels)

    def get_channel(self, channel_id: str) -> dict[str, Any] | None:
        return self.get_item(f"CH#{channel_id}", "META") or self.get_item(f"CHANNEL#{channel_id}", "META")

    def put_channel(self, channel: dict[str, Any]) -> dict[str, Any]:
        channel_id = channel["channel_id"]
        saved = self.put_item(channel_item(channel, self.get_channel(channel_id)))
        self.put_item(channel_ref_item(saved))
        return saved

    def get_artifact_by_id(self, artifact_id: str) -> dict[str, Any] | None:
        if ":" in artifact_id:
            video_id, artifact_type = artifact_id.split(":", 1)
            matches = [item for item in self.list_artifacts(video_id) if item.get("artifact_type") == artifact_type]
            if matches:
                matches.sort(key=lambda item: item.get("generated_at", ""), reverse=True)
                return deepcopy(matches[0])
            return self.get_item(f"VIDEO#{video_id}", f"ARTIFACT#{artifact_type}")
        for item in self.items.values():
            if item.get("item_type") == "Artifact" and item.get("artifact_id") == artifact_id:
                return deepcopy(item)
        return None

    def list_quota_usage(self, limit: int = 100) -> list[dict[str, Any]]:
        usage = [item for item in self.items.values() if item.get("item_type") == "QuotaUsage" and not item.get("sk", "").startswith("METHOD#")]
        usage.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return deepcopy(usage[:limit])


class DynamoRepository(MemoryRepository):
    """DynamoDB adapter with a memory-compatible surface for tests and Lambda.

    The implementation intentionally uses the high-level Table resource so the
    stored document shape matches the item schema documented in README.
    """

    def __init__(self, table_name: str | None = None) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for DynamoRepository")
        self.table_name = table_name or os.environ["DIOPSIDE_TABLE_NAME"]
        self.table = boto3.resource("dynamodb").Table(self.table_name)
        self.idempotency_index = {}

    def put_item(self, item: dict[str, Any]) -> dict[str, Any]:
        if item.get("item_type") not in ITEM_TYPES:
            raise ValueError(f"unsupported item_type: {item.get('item_type')}")
        existing = self.get_item(item["pk"], item["sk"])
        normalized = normalize_item_metadata(item, existing)
        self.table.put_item(Item=normalized)
        return deepcopy(normalized)

    def get_item(self, pk: str, sk: str) -> dict[str, Any] | None:
        item = self.table.get_item(Key={"pk": pk, "sk": sk}).get("Item")
        return deepcopy(item) if item else None

    def delete_item(self, pk: str, sk: str) -> None:
        self.table.delete_item(Key={"pk": pk, "sk": sk})

    def create_job(self, job_type: str, payload: dict[str, Any], idempotency_key: str) -> tuple[dict[str, Any], bool]:
        job_id = stable_id("job", idempotency_key)
        stamp = now_iso()
        target_type, target_id = job_target(payload, job_type)
        item = {
            "item_type": "Job",
            "pk": f"JOB#{job_id}",
            "sk": "META",
            "job_id": job_id,
            "job_type": job_type,
            "target_type": target_type,
            "target_id": target_id,
            "dedupe_key": idempotency_key,
            "idempotency_key": idempotency_key,
            "input": payload,
            "payload": payload,
            "latest_state": "queued",
            "derived_state": "queued",
            "attempt": 0,
            "max_attempts": int(payload.get("max_attempts") or 3),
            "queued_at": stamp,
            "next_run_at": payload.get("next_run_at") or stamp,
            "created_at": stamp,
            "updated_at": stamp,
            "gsi3pk": "JOB#STATE#queued",
            "gsi3sk": f"NEXT#{payload.get('next_run_at') or stamp}#{job_id}",
        }
        item = normalize_item_metadata(item)
        try:
            self.table.put_item(Item=item, ConditionExpression="attribute_not_exists(pk)")
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                raise
            existing = self.get_job(job_id)
            if existing:
                self.put_item(idempotency_item(idempotency_key, job_id, job_type, payload))
                return existing, True
            raise
        self.put_item(idempotency_item(idempotency_key, job_id, job_type, payload))
        self.append_job_event(job_id, "queued", {"job_type": job_type})
        return self.get_job(job_id) or item, False

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.get_item(f"JOB#{job_id}", "META")
        if not job:
            return None
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        response = self.table.query(KeyConditionExpression=Key("pk").eq(f"JOB#{job_id}"))
        events = normalize_job_events([item for item in response.get("Items", []) if item.get("item_type") == "JobEvent"])
        job["events"] = deepcopy(events)
        latest_state = derive_job_state(events)
        job["latest_state"] = latest_state
        job["derived_state"] = latest_state
        return job

    def append_job_event(self, job_id: str, event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        response = self.table.query(KeyConditionExpression=Key("pk").eq(f"JOB#{job_id}"))
        events = [item for item in response.get("Items", []) if item.get("item_type") == "JobEvent"]
        event = self.put_item(job_event_item(job_id, event_type, details, next_job_event_seq(events)))
        job = self.get_item(f"JOB#{job_id}", "META")
        if job:
            updated_events = normalize_job_events([*events, event])
            self.put_item(update_job_read_model(job, derive_job_state(updated_events)))
        return event

    def acquire_lock(self, lock_key: str, owner_job_id: str, ttl_seconds: int = 900, owner_request_id: str | None = None) -> dict[str, Any] | None:
        item = normalize_item_metadata(lock_item(lock_key, owner_job_id, ttl_seconds, owner_request_id))
        now = int(time.time())
        try:
            self.table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(pk) OR expires_at < :now OR owner_job_id = :owner_job_id",
                ExpressionAttributeValues={":now": now, ":owner_job_id": owner_job_id},
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return None
            raise
        return deepcopy(item)

    def release_lock(self, lock_key: str, owner_job_id: str) -> bool:
        try:
            self.table.delete_item(
                Key={"pk": f"LOCK#{lock_key}", "sk": "META"},
                ConditionExpression="owner_job_id = :owner_job_id",
                ExpressionAttributeValues={":owner_job_id": owner_job_id},
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            raise
        return True

    def list_videos(self, limit: int = 100) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        videos = [
            item
            for item in self._query_all(
                IndexName="by_public_date",
                KeyConditionExpression=Key("gsi1pk").eq("VIDEO#PUBLIC"),
                ScanIndexForward=True,
                Limit=limit,
            )
            if item.get("item_type") == "Video" and item.get("public", True)
        ]
        return deepcopy(videos[:limit])

    def list_video_month_indexes(self, year: int | None = None, month: int | None = None) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        if year is None:
            return super().list_video_month_indexes(year=year, month=month)
        months = [month] if month is not None else list(range(1, 13))
        items: list[dict[str, Any]] = []
        for month_value in months:
            yyyy_mm_key = f"{year:04d}{month_value:02d}"
            items.extend(
                self._query_all(
                    IndexName="by_public_date",
                    KeyConditionExpression=Key("gsi1pk").eq(f"VIDEO#MONTH#{yyyy_mm_key}"),
                    ScanIndexForward=False,
                    Limit=10000,
                )
            )
        items = [item for item in items if item.get("item_type") == "VideoMonthIndex"]
        if not items:
            return super().list_video_month_indexes(year=year, month=month)
        items.sort(key=lambda item: item.get("published_at", ""), reverse=True)
        return deepcopy(items)

    def list_random_videos(self, limit: int = 1000) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        items = self._query_all(
            KeyConditionExpression=Key("pk").eq("RANDOM#DEFAULT") & Key("sk").begins_with("VID#"),
            Limit=limit,
        )
        items = [item for item in items if item.get("item_type") == "RandomBucket"]
        items.sort(key=lambda item: item.get("sk", ""))
        return deepcopy(items[:limit])

    def list_tags(self) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        summaries = self._query_all(
            IndexName="by_tag",
            KeyConditionExpression=Key("gsi2pk").eq("TAG#SUMMARY"),
            Limit=10000,
        )
        summaries = [item for item in summaries if item.get("item_type") == "TagSummary"]
        if summaries:
            summaries = [item for item in summaries if item.get("public_visible", True)]
            summaries.sort(key=lambda item: (int(item.get("sort_order", 0)), item.get("label", "")))
            return deepcopy(summaries)
        return super().list_tags()

    def list_static_exports(self, limit: int = 20) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        items = self._query_all(
            KeyConditionExpression=Key("pk").eq("EXPORT#public") & Key("sk").begins_with("VERSION#"),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = [item for item in items if item.get("item_type") == "StaticExport"]
        items.sort(key=lambda item: item.get("exported_at", ""), reverse=True)
        return deepcopy(items[:limit])

    def list_jobs(self, limit: int = 50) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        job_items: list[dict[str, Any]] = []
        for state in (*JOB_LIST_STATES, "ALL"):
            key = f"JOB#STATE#{state}" if state != "ALL" else "JOB#ALL"
            job_items.extend(
                self._query_all(
                    IndexName="by_work_queue",
                    KeyConditionExpression=Key("gsi3pk").eq(key),
                    ScanIndexForward=True,
                    Limit=limit,
                )
            )
        seen: set[str] = set()
        unique_job_items: list[dict[str, Any]] = []
        for item in job_items:
            job_id = str(item.get("job_id") or "")
            if job_id and job_id not in seen:
                seen.add(job_id)
                unique_job_items.append(item)
        jobs = [self.get_job(item["job_id"]) for item in unique_job_items if item.get("item_type") == "Job"]
        jobs = [job for job in jobs if job]
        jobs.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return deepcopy(jobs[:limit])

    def list_artifacts(self, video_id: str) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        items = []
        for pk in [f"VID#{video_id}", f"VIDEO#{video_id}"]:
            response = self.table.query(KeyConditionExpression=Key("pk").eq(pk))
            items.extend(item for item in response.get("Items", []) if item.get("item_type") == "Artifact")
        items.sort(key=lambda item: (item.get("artifact_type", ""), item.get("artifact_version", ""), item.get("generated_at", "")))
        return deepcopy(items)

    def list_chat_chunks(self, video_id: str) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        response = self.table.query(KeyConditionExpression=Key("pk").eq(f"VID#{video_id}"))
        chunks = [item for item in response.get("Items", []) if item.get("item_type") == "ChatPageManifest"]
        if not chunks:
            response = self.table.query(KeyConditionExpression=Key("pk").eq(f"VIDEO#{video_id}"))
            chunks = [item for item in response.get("Items", []) if item.get("item_type") == "ChatMessageChunkManifest"]
        chunks.sort(key=lambda item: (int(item.get("seq", 0)), item.get("sk", "")))
        return deepcopy(chunks)

    def list_channels(self) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        refs = self._query_all(
            KeyConditionExpression=Key("pk").eq("APP#CHANNELS") & Key("sk").begins_with("CH#"),
            Limit=1000,
        )
        refs = [item for item in refs if item.get("item_type") == "ChannelRef"]
        if refs:
            refs.sort(key=lambda item: (int(item.get("priority", 100)), item.get("channel_id", "")))
            return deepcopy(refs)
        return super().list_channels()

    def get_artifact_by_id(self, artifact_id: str) -> dict[str, Any] | None:
        if ":" in artifact_id:
            video_id, artifact_type = artifact_id.split(":", 1)
            return self.get_item(f"VIDEO#{video_id}", f"ARTIFACT#{artifact_type}")
        return None

    def list_quota_usage(self, limit: int = 100) -> list[dict[str, Any]]:
        if Key is None:
            raise RuntimeError("boto3.dynamodb.conditions.Key is required")
        usage = [
            item
            for item in self._query_all(
                IndexName="by_work_queue",
                KeyConditionExpression=Key("gsi3pk").eq("QUOTA#ALL"),
                ScanIndexForward=False,
                Limit=limit,
            )
            if item.get("item_type") == "QuotaUsage" and not item.get("sk", "").startswith("METHOD#")
        ]
        return deepcopy(usage[:limit])

    def _query_all(self, **kwargs: Any) -> list[dict[str, Any]]:
        limit = int(kwargs.pop("Limit", 100))
        items: list[dict[str, Any]] = []
        request = {**kwargs, "Limit": limit}
        while len(items) < limit:
            response = self.table.query(**request)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            request["ExclusiveStartKey"] = last_key
            request["Limit"] = max(1, limit - len(items))
        return items[:limit]
